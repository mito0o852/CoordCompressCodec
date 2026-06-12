"""Public encoder and decoder API for coordinate compression."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Sequence

from .tokenizer import bytes_to_tokens, tokens_to_bytes
from .universe import CoordinateUniverse


@dataclass(frozen=True)
class EncodedPayload:
    """In-memory encoded coordinate payload.

    Args:
        symbols: Coordinate symbol stream produced by ``DcEncoder``. Symbols
            below ``256`` are literal bytes; symbols at or above ``256`` are
            coordinate IDs from the active universe.
        original_size: Original input size in bytes.
        checksum: SHA-256 checksum of the original bytes. The decoder uses this
            to verify exact reconstruction.
    """

    symbols: tuple[int, ...]
    original_size: int
    checksum: str

    @property
    def symbol_count(self) -> int:
        """Number of symbols in the encoded coordinate stream."""

        return len(self.symbols)

    @property
    def symbol_ratio(self) -> float:
        """Encoded symbol count divided by original byte count."""

        return self.symbol_count / max(1, self.original_size)

    def preview(self, limit: int = 24) -> str:
        """Return a compact human-readable symbol preview.

        Args:
            limit: Maximum number of symbols to include before appending an
                ellipsis.

        Returns:
            Preview string using ``B`` for literal byte symbols and ``C`` for
            coordinate symbols.
        """

        parts = []
        for symbol in self.symbols[:limit]:
            prefix = "B" if symbol < 256 else "C"
            parts.append(f"{prefix}{symbol}")
        if len(self.symbols) > limit:
            parts.append("...")
        return " ".join(parts)


class DcEncoder:
    """Encode bytes or text into reversible coordinate-compressed payloads.

    ``DcEncoder`` is the main public entry point for compression. It converts
    input into byte tokens, applies the configured coordinate universe, and
    returns an ``EncodedPayload`` that can later be decoded exactly with
    ``DcDecoder``.

    Args:
        universe: Coordinate mapping used to fold token sequences into
            coordinate symbols. If omitted, an empty universe is used, which
            preserves roundtrip behavior but does not compress.

    Example:
        >>> from src import UniverseBuilder, DcEncoder
        >>> universe, _ = UniverseBuilder().fit_text("Hello Hello Hello")
        >>> payload = DcEncoder(universe).encode("Hello Hello")
        >>> payload.symbol_count < len("Hello Hello")
        True
    """

    def __init__(self, universe: CoordinateUniverse | None = None) -> None:
        self.universe = universe or CoordinateUniverse.empty()

    def encode(self, text: str) -> EncodedPayload:
        """Encode UTF-8 text into a reversible coordinate payload.

        Args:
            text: Input text to encode. It is converted to UTF-8 bytes before
                tokenization.

        Returns:
            Encoded payload containing coordinate symbols, original byte length,
            and checksum.

        Raises:
            UnicodeEncodeError: If ``text`` cannot be encoded as UTF-8.
        """

        return self.encode_bytes(text.encode("utf-8"))

    def encode_bytes(self, data: bytes) -> EncodedPayload:
        """Encode raw bytes into a reversible coordinate payload.

        Args:
            data: Raw bytes to encode.

        Returns:
            Encoded coordinate payload.
        """

        tokens = bytes_to_tokens(data)
        symbols = self.universe.encode(tokens)
        return EncodedPayload(
            symbols=tuple(symbols),
            original_size=len(data),
            checksum=sha256(data).hexdigest(),
        )


class DcDecoder:
    """Decode coordinate payloads back to exact bytes or text.

    Args:
        universe: The same compatible coordinate universe used during encoding.

    Example:
        >>> from src import DcDecoder
        >>> decoded = DcDecoder(universe).decode(payload)
        >>> decoded == "Hello Hello"
        True
    """

    def __init__(self, universe: CoordinateUniverse) -> None:
        self.universe = universe

    def decode(self, payload: EncodedPayload) -> str:
        """Decode a coordinate payload back to UTF-8 text.

        Args:
            payload: Encoded payload produced by ``DcEncoder`` with a compatible
                universe.

        Returns:
            Reconstructed text.

        Raises:
            ValueError: If checksum verification fails.
            UnicodeDecodeError: If the reconstructed bytes are not valid UTF-8.
        """

        return self.decode_to_bytes(payload).decode("utf-8")

    def decode_to_bytes(self, payload: EncodedPayload) -> bytes:
        """Decode a coordinate payload back to raw bytes.

        Args:
            payload: Encoded payload produced by ``DcEncoder``.

        Returns:
            Exact reconstructed byte string.

        Raises:
            ValueError: If checksum verification fails.
        """

        tokens = self.universe.decode(payload.symbols)
        data = tokens_to_bytes(tokens)
        if len(data) != payload.original_size:
            raise ValueError("Decoded size does not match payload metadata.")
        checksum = sha256(data).hexdigest()
        if checksum != payload.checksum:
            raise ValueError("Decoded payload failed checksum verification.")
        return data


def payload_from_symbols(symbols: Sequence[int], *, original: bytes) -> EncodedPayload:
    """Create a payload from an existing symbol stream and original bytes.

    Args:
        symbols: Encoded coordinate symbols.
        original: Original bytes used to compute size and checksum metadata.

    Returns:
        ``EncodedPayload`` instance.
    """

    return EncodedPayload(
        symbols=tuple(int(symbol) for symbol in symbols),
        original_size=len(original),
        checksum=sha256(original).hexdigest(),
    )
