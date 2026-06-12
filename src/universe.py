"""Coordinate universe definitions and reversible encode/decode logic.

A coordinate universe is the shared dictionary used by the codec. Base IDs
``0..255`` represent raw bytes. Coordinate IDs above that range represent
reversible folds such as:

    ``(72, 101, 108, 108, 111) -> 256``

Layers are applied in order during encoding and reversed recursively during
decoding. The universe is therefore lossless as long as every coordinate node
stores its exact expansion.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from .tokenizer import BYTE_VOCAB_SIZE


@dataclass(frozen=True)
class CoordinateNode:
    """A single reversible coordinate definition.

    Args:
        node_id: Integer ID emitted by the encoder when this node matches.
        expansion: Exact token sequence replaced by ``node_id``. Expansions may
            contain byte IDs and coordinate IDs from earlier layers.
        layer: One-based coordinate layer. Layer ``1`` folds byte tokens, layer
            ``2`` folds the output of layer ``1``, and so on.
        frequency: Number of times this node was active in the build corpus
            after greedy matching and pruning.
    """

    node_id: int
    expansion: tuple[int, ...]
    layer: int
    frequency: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize the node into a JSON-compatible dictionary."""

        return {
            "node_id": self.node_id,
            "expansion": list(self.expansion),
            "layer": self.layer,
            "frequency": self.frequency,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CoordinateNode":
        """Create a node from a JSON-compatible dictionary.

        Args:
            value: Dictionary produced by ``CoordinateNode.to_dict``.

        Returns:
            A validated ``CoordinateNode`` instance.

        Raises:
            ValueError: If required fields are missing or malformed.
        """

        try:
            node_id = int(value["node_id"])
            expansion = tuple(int(item) for item in value["expansion"])
            layer = int(value["layer"])
            frequency = int(value.get("frequency", 0))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Malformed coordinate node: {value!r}") from exc
        return cls(node_id=node_id, expansion=expansion, layer=layer, frequency=frequency)


class CoordinateUniverse:
    """Shared coordinate dictionary used for reversible compression.

    ``CoordinateUniverse`` owns all coordinate layers and provides the exact
    transformation used by both the encoder and decoder. Encoding greedily
    applies each layer from shallowest to deepest. Decoding recursively expands
    coordinate IDs back to byte IDs.

    Args:
        layers: Coordinate layers. Each layer is a sequence of
            ``CoordinateNode`` objects. Node IDs must be unique across all
            layers.
        version: Human-readable universe version string stored in serialized
            files.

    Example:
        >>> node = CoordinateNode(256, (72, 105), layer=1, frequency=3)
        >>> universe = CoordinateUniverse(layers=((node,),))
        >>> universe.encode([72, 105, 33])
        [256, 33]
        >>> universe.decode([256, 33])
        [72, 105, 33]
    """

    def __init__(
        self,
        layers: Sequence[Sequence[CoordinateNode]] = (),
        *,
        version: str = "dc-v1",
    ) -> None:
        self.version = version
        self.layers: tuple[tuple[CoordinateNode, ...], ...] = tuple(tuple(layer) for layer in layers)
        self._by_id: dict[int, CoordinateNode] = {}
        self._layer_indexes: list[dict[tuple[int, ...], CoordinateNode]] = []
        self._layer_lengths: list[list[int]] = []
        self._validate_and_index()

    @classmethod
    def empty(cls) -> "CoordinateUniverse":
        """Return a universe with no coordinate nodes.

        Returns:
            A pass-through universe. It roundtrips exactly but performs no
            compression because it only emits base byte IDs.
        """

        return cls()

    @property
    def node_count(self) -> int:
        """Total number of coordinate nodes across all layers."""

        return sum(len(layer) for layer in self.layers)

    @property
    def layer_count(self) -> int:
        """Number of coordinate layers in the universe."""

        return len(self.layers)

    @property
    def vocab_size(self) -> int:
        """Highest usable symbol count including base byte IDs."""

        if not self._by_id:
            return BYTE_VOCAB_SIZE
        return max(self._by_id) + 1

    def encode(self, tokens: Sequence[int]) -> list[int]:
        """Encode byte tokens into layered coordinate symbols.

        Args:
            tokens: Sequence of base byte IDs. Values must be in the range
                ``0..255`` when passed into the first layer.

        Returns:
            Encoded symbol IDs after all coordinate layers have been applied.

        Raises:
            ValueError: If a base token is outside the valid byte range.
        """

        self._validate_base_tokens(tokens)
        current = list(tokens)
        for layer_index in range(len(self.layers)):
            current = self.encode_layer(current, layer_index)
        return current

    def encode_layer(self, tokens: Sequence[int], layer_index: int) -> list[int]:
        """Apply exactly one coordinate layer using greedy longest matching.

        Args:
            tokens: Input symbols for this layer.
            layer_index: Zero-based layer index.

        Returns:
            Symbol sequence after applying the requested layer.

        Raises:
            IndexError: If ``layer_index`` does not exist.
        """

        expansion_index = self._layer_indexes[layer_index]
        lengths = self._layer_lengths[layer_index]
        output: list[int] = []
        index = 0
        while index < len(tokens):
            matched: CoordinateNode | None = None
            for length in lengths:
                if index + length > len(tokens):
                    continue
                matched = expansion_index.get(tuple(tokens[index:index + length]))
                if matched is not None:
                    break
            if matched is None:
                output.append(tokens[index])
                index += 1
            else:
                output.append(matched.node_id)
                index += len(matched.expansion)
        return output

    def decode(self, symbols: Sequence[int]) -> list[int]:
        """Decode coordinate symbols back into base byte tokens.

        Args:
            symbols: Encoded coordinate stream.

        Returns:
            Exact byte-token sequence represented by ``symbols``.

        Raises:
            ValueError: If the stream contains an unknown coordinate ID or a
                recursive coordinate cycle.
        """

        output: list[int] = []
        for symbol in symbols:
            self._expand_symbol(int(symbol), output, seen=set())
        self._validate_base_tokens(output)
        return output

    def to_dict(self) -> dict[str, Any]:
        """Serialize the universe into a JSON-compatible dictionary."""

        return {
            "version": self.version,
            "base_vocab_size": BYTE_VOCAB_SIZE,
            "layers": [[node.to_dict() for node in layer] for layer in self.layers],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CoordinateUniverse":
        """Create a universe from a JSON-compatible dictionary.

        Args:
            value: Dictionary produced by ``CoordinateUniverse.to_dict``.

        Returns:
            A validated coordinate universe.

        Raises:
            ValueError: If the serialized universe is malformed.
        """

        if int(value.get("base_vocab_size", BYTE_VOCAB_SIZE)) != BYTE_VOCAB_SIZE:
            raise ValueError("Unsupported base vocabulary size.")
        layers = [
            [CoordinateNode.from_dict(item) for item in layer]
            for layer in value.get("layers", [])
        ]
        return cls(layers=layers, version=str(value.get("version", "dc-v1")))

    def save(self, path: str | Path) -> None:
        """Write the universe to disk as formatted JSON.

        Args:
            path: Destination file path.
        """

        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CoordinateUniverse":
        """Load a universe JSON file from disk.

        Args:
            path: Path to a universe file created by ``save``.

        Returns:
            A validated coordinate universe.
        """

        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def fingerprint(self) -> str:
        """Return a stable SHA-256 hash of this universe.

        Returns:
            Hex digest computed from canonical JSON. Payload files store this
            fingerprint so decoders can detect mismatched universes.
        """

        encoded = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _validate_and_index(self) -> None:
        seen_ids: set[int] = set()
        for layer_number, layer in enumerate(self.layers, start=1):
            layer_index: dict[tuple[int, ...], CoordinateNode] = {}
            for node in layer:
                if node.node_id < BYTE_VOCAB_SIZE:
                    raise ValueError(f"Coordinate ID {node.node_id} overlaps byte IDs.")
                if node.node_id in seen_ids:
                    raise ValueError(f"Duplicate coordinate ID: {node.node_id}")
                if node.layer != layer_number:
                    raise ValueError(f"Node {node.node_id} has incorrect layer {node.layer}.")
                if len(node.expansion) < 2:
                    raise ValueError(f"Node {node.node_id} expansion must contain at least two symbols.")
                if node.node_id in node.expansion:
                    raise ValueError(f"Node {node.node_id} directly expands to itself.")
                seen_ids.add(node.node_id)
                self._by_id[node.node_id] = node
                layer_index[node.expansion] = node
            self._layer_indexes.append(layer_index)
            self._layer_lengths.append(sorted({len(node.expansion) for node in layer}, reverse=True))

    def _expand_symbol(self, symbol: int, output: list[int], *, seen: set[int]) -> None:
        if 0 <= symbol < BYTE_VOCAB_SIZE:
            output.append(symbol)
            return
        node = self._by_id.get(symbol)
        if node is None:
            raise ValueError(f"Unknown coordinate symbol: {symbol}")
        if symbol in seen:
            raise ValueError(f"Coordinate cycle detected at symbol {symbol}.")
        seen.add(symbol)
        for child in node.expansion:
            self._expand_symbol(child, output, seen=seen)
        seen.remove(symbol)

    @staticmethod
    def _validate_base_tokens(tokens: Iterable[int]) -> None:
        for token in tokens:
            if not 0 <= int(token) < BYTE_VOCAB_SIZE:
                raise ValueError(f"Base token {token!r} is outside byte range 0..255.")
