"""Coordinate universe builder.

The builder learns reversible coordinate folds from example bytes. It is the
official V1 implementation of the recursive idea:

    bytes -> layer 1 coordinates -> layer 2 coordinates -> ...

Each accepted node stores its exact expansion, so the resulting universe is
lossless by construction.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .selector import select_candidates
from .tokenizer import BYTE_VOCAB_SIZE, bytes_to_tokens
from .universe import CoordinateNode, CoordinateUniverse


@dataclass(frozen=True)
class LayerBuildReport:
    """Build statistics for one coordinate layer.

    Args:
        layer: One-based layer number.
        candidates: Number of candidate folds considered.
        accepted_nodes: Number of nodes kept after active-count pruning.
        input_symbols: Total symbols before this layer.
        output_symbols: Total symbols after this layer.
    """

    layer: int
    candidates: int
    accepted_nodes: int
    input_symbols: int
    output_symbols: int

    @property
    def ratio(self) -> float:
        """Layer output-symbol ratio relative to input symbols."""

        return self.output_symbols / max(1, self.input_symbols)


@dataclass(frozen=True)
class BuildReport:
    """Summary returned by ``UniverseBuilder.fit_*`` methods.

    Args:
        original_symbols: Total byte symbols in the build corpus.
        final_symbols: Total symbols after all coordinate layers.
        layer_reports: Per-layer build statistics.
    """

    original_symbols: int
    final_symbols: int
    layer_reports: tuple[LayerBuildReport, ...]

    @property
    def ratio(self) -> float:
        """Final symbol ratio relative to original byte symbols."""

        return self.final_symbols / max(1, self.original_symbols)


@dataclass(frozen=True)
class BuilderConfig:
    """Configuration for recursive coordinate universe construction.

    Args:
        max_layers: Maximum number of coordinate layers to build.
        max_nodes_per_layer: Maximum nodes kept in each layer.
        max_ngram: Maximum phrase length considered for a coordinate expansion.
        min_count: Minimum raw candidate frequency.
        active_min_count: Minimum frequency after greedy matching. This removes
            candidates that looked good in raw counts but are rarely used once
            stronger candidates are applied first.
    """

    max_layers: int = 2
    max_nodes_per_layer: int = 4096
    max_ngram: int = 12
    min_count: int = 3
    active_min_count: int = 2


class UniverseBuilder:
    """Build layered coordinate universes from text or bytes.

    Args:
        config: Build configuration. If omitted, conservative defaults are used
            for a small but useful V1 universe.

    Example:
        >>> builder = UniverseBuilder()
        >>> universe, report = builder.fit_texts(["Hello Hello Hello"])
        >>> report.ratio < 1.0
        True
    """

    def __init__(self, config: BuilderConfig | None = None) -> None:
        self.config = config or BuilderConfig()

    def fit_text(self, text: str) -> tuple[CoordinateUniverse, BuildReport]:
        """Build a universe from one text string.

        Args:
            text: UTF-8 text used to learn coordinate folds.

        Returns:
            ``(universe, report)`` where ``universe`` can encode/decode data and
            ``report`` describes the achieved symbol reduction on the build
            corpus.
        """

        return self.fit_bytes([text.encode("utf-8")])

    def fit_texts(self, texts: Sequence[str]) -> tuple[CoordinateUniverse, BuildReport]:
        """Build a universe from multiple text documents.

        Args:
            texts: Training corpus. Documents are encoded as UTF-8 bytes before
                coordinate selection.

        Returns:
            A coordinate universe and build report.
        """

        return self.fit_bytes([text.encode("utf-8") for text in texts])

    def fit_bytes(self, documents: Sequence[bytes]) -> tuple[CoordinateUniverse, BuildReport]:
        """Build a universe from byte documents.

        Args:
            documents: Training corpus represented as byte strings.

        Returns:
            A coordinate universe and build report.

        Raises:
            ValueError: If no documents are provided.
        """

        if not documents:
            raise ValueError("UniverseBuilder requires at least one document.")

        current_docs = [bytes_to_tokens(document) for document in documents]
        original_symbols = sum(len(document) for document in current_docs)
        layers: list[tuple[CoordinateNode, ...]] = []
        reports: list[LayerBuildReport] = []
        next_node_id = BYTE_VOCAB_SIZE

        for layer_number in range(1, self.config.max_layers + 1):
            input_symbols = sum(len(document) for document in current_docs)
            candidates = select_candidates(
                current_docs,
                max_nodes=self.config.max_nodes_per_layer,
                max_ngram=self.config.max_ngram,
                min_count=self.config.min_count,
            )
            if not candidates:
                break

            draft_nodes = [
                CoordinateNode(
                    node_id=next_node_id + index,
                    expansion=candidate.expansion,
                    layer=layer_number,
                    frequency=candidate.frequency,
                )
                for index, candidate in enumerate(candidates)
            ]
            encoded_docs = [_encode_one_layer(document, draft_nodes) for document in current_docs]
            active_counts = _active_coordinate_counts(encoded_docs, start_id=next_node_id)
            kept_drafts = [
                node for node in draft_nodes
                if active_counts[node.node_id] >= self.config.active_min_count
            ]
            if not kept_drafts:
                break

            final_nodes = tuple(
                CoordinateNode(
                    node_id=next_node_id + index,
                    expansion=node.expansion,
                    layer=layer_number,
                    frequency=active_counts[node.node_id],
                )
                for index, node in enumerate(kept_drafts)
            )
            encoded_docs = [_encode_one_layer(document, final_nodes) for document in current_docs]
            output_symbols = sum(len(document) for document in encoded_docs)
            layers.append(final_nodes)
            reports.append(
                LayerBuildReport(
                    layer=layer_number,
                    candidates=len(candidates),
                    accepted_nodes=len(final_nodes),
                    input_symbols=input_symbols,
                    output_symbols=output_symbols,
                )
            )
            current_docs = encoded_docs
            next_node_id += len(final_nodes)

        universe = CoordinateUniverse(layers=tuple(layers))
        final_symbols = sum(len(document) for document in current_docs)
        return universe, BuildReport(
            original_symbols=original_symbols,
            final_symbols=final_symbols,
            layer_reports=tuple(reports),
        )


def _encode_one_layer(tokens: Sequence[int], nodes: Sequence[CoordinateNode]) -> list[int]:
    expansion_index = {node.expansion: node for node in nodes}
    lengths = sorted({len(node.expansion) for node in nodes}, reverse=True)
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


def _active_coordinate_counts(encoded_docs: Sequence[Sequence[int]], *, start_id: int) -> Counter[int]:
    counts: Counter[int] = Counter()
    for document in encoded_docs:
        for symbol in document:
            if symbol >= start_id:
                counts[symbol] += 1
    return counts
