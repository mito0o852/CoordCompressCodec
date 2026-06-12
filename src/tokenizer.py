"""Byte-preserving tokenization utilities for coordinate compression.

The codec intentionally starts from bytes instead of words or Unicode code
points. Byte tokenization makes the compression path exact for any input file:
plain text, JSON, CSV, logs, source code, or arbitrary UTF-8 text. Higher-level
coordinate nodes can still learn words and phrases because those words appear
as repeated byte sequences.
"""

from __future__ import annotations

from typing import Iterable


BYTE_VOCAB_SIZE = 256


def bytes_to_tokens(data: bytes) -> list[int]:
    """Convert raw bytes into base token IDs.

    Args:
        data: Input byte string. Each byte is represented by one integer token
            in the inclusive range ``0`` through ``255``.

    Returns:
        A list of integer byte tokens. The returned sequence is exactly the same
        length as ``data``.

    Example:
        >>> bytes_to_tokens(b"Hi")
        [72, 105]
    """

    return list(data)


def tokens_to_bytes(tokens: Iterable[int]) -> bytes:
    """Convert byte token IDs back into raw bytes.

    Args:
        tokens: Iterable of integer tokens. Every token must be in the inclusive
            range ``0`` through ``255``.

    Returns:
        The byte string represented by the input token IDs.

    Raises:
        ValueError: If any token is outside the valid byte range.

    Example:
        >>> tokens_to_bytes([72, 105])
        b'Hi'
    """

    output = bytearray()
    for token in tokens:
        if not 0 <= token < BYTE_VOCAB_SIZE:
            raise ValueError(f"Token {token!r} is not a byte token.")
        output.append(token)
    return bytes(output)


def text_to_tokens(text: str, *, encoding: str = "utf-8") -> list[int]:
    """Encode text into byte tokens.

    Args:
        text: Text to tokenize.
        encoding: Character encoding used to convert the text into bytes.
            ``"utf-8"`` is the default and recommended value.

    Returns:
        A byte-token sequence suitable for coordinate encoding.

    Raises:
        UnicodeEncodeError: If the text cannot be encoded with ``encoding``.
    """

    return bytes_to_tokens(text.encode(encoding))


def tokens_to_text(tokens: Iterable[int], *, encoding: str = "utf-8") -> str:
    """Decode byte tokens back into text.

    Args:
        tokens: Iterable of byte token IDs in the inclusive range ``0`` through
            ``255``.
        encoding: Character encoding used to decode the reconstructed bytes.

    Returns:
        Decoded text.

    Raises:
        ValueError: If any token is outside the valid byte range.
        UnicodeDecodeError: If the reconstructed bytes are invalid for
            ``encoding``.
    """

    return tokens_to_bytes(tokens).decode(encoding)
