"""DCC1 payload file format.

The file format stores an encoded coordinate stream, not the universe itself.
This keeps payloads small for shared-universe workflows. Decoding requires the
matching universe JSON file; the payload header stores its fingerprint so a
mismatch is caught before reconstruction.
"""

from __future__ import annotations

import bz2
import json
import lzma
import struct
import zlib
from typing import Literal

from .codec import EncodedPayload
from .universe import CoordinateUniverse


MAGIC = b"DCC1"
Wrapper = Literal["none", "zlib", "lzma", "bz2", "best"]


def pack_payload(
    payload: EncodedPayload,
    *,
    universe: CoordinateUniverse,
    wrapper: Wrapper = "best",
) -> bytes:
    """Serialize an encoded payload into DCC1 bytes.

    Args:
        payload: Encoded coordinate payload.
        universe: Universe used to encode the payload. Its fingerprint is stored
            in the header for decode-time validation.
        wrapper: Final entropy wrapper. ``"best"`` tries ``none``, ``zlib``,
            ``lzma``, and ``bz2`` and keeps the smallest body.

    Returns:
        Complete DCC1 file bytes.
    """

    raw_body = encode_varints(payload.symbols)
    chosen_wrapper, body = apply_wrapper(raw_body, wrapper)
    header = {
        "version": 1,
        "wrapper": chosen_wrapper,
        "original_size": payload.original_size,
        "checksum": payload.checksum,
        "symbol_count": len(payload.symbols),
        "universe_hash": universe.fingerprint(),
    }
    header_bytes = json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return MAGIC + struct.pack(">I", len(header_bytes)) + header_bytes + body


def unpack_payload(data: bytes, *, universe: CoordinateUniverse | None = None) -> EncodedPayload:
    """Parse DCC1 bytes into an in-memory payload.

    Args:
        data: Bytes created by ``pack_payload``.
        universe: Optional universe used to validate the stored fingerprint.

    Returns:
        Encoded payload ready for ``DcDecoder``.

    Raises:
        ValueError: If the file is malformed or the universe fingerprint does
            not match.
    """

    if len(data) < 8 or data[:4] != MAGIC:
        raise ValueError("Input is not a DCC1 payload.")
    header_size = struct.unpack(">I", data[4:8])[0]
    header_start = 8
    header_end = header_start + header_size
    if header_end > len(data):
        raise ValueError("DCC1 header length exceeds file size.")
    header = json.loads(data[header_start:header_end].decode("utf-8"))
    if universe is not None and header.get("universe_hash") != universe.fingerprint():
        raise ValueError("Payload was encoded with a different coordinate universe.")
    body = remove_wrapper(data[header_end:], str(header["wrapper"]))
    symbols = tuple(decode_varints(body))
    if len(symbols) != int(header["symbol_count"]):
        raise ValueError("Decoded symbol count does not match DCC1 header.")
    return EncodedPayload(
        symbols=symbols,
        original_size=int(header["original_size"]),
        checksum=str(header["checksum"]),
    )


def encode_varints(values: tuple[int, ...] | list[int]) -> bytes:
    """Encode non-negative integers as unsigned varints."""

    output = bytearray()
    for value in values:
        integer = int(value)
        if integer < 0:
            raise ValueError("Varint values must be non-negative.")
        while integer >= 0x80:
            output.append((integer & 0x7F) | 0x80)
            integer >>= 7
        output.append(integer)
    return bytes(output)


def decode_varints(data: bytes) -> list[int]:
    """Decode unsigned varints from bytes."""

    values: list[int] = []
    value = 0
    shift = 0
    for byte in data:
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
            if shift > 63:
                raise ValueError("Varint is too large.")
            continue
        values.append(value)
        value = 0
        shift = 0
    if shift:
        raise ValueError("Truncated varint stream.")
    return values


def apply_wrapper(data: bytes, wrapper: Wrapper) -> tuple[str, bytes]:
    """Apply a final entropy wrapper to encoded symbol bytes."""

    if wrapper == "none":
        return "none", data
    if wrapper == "zlib":
        return "zlib", zlib.compress(data, level=9)
    if wrapper == "lzma":
        return "lzma", lzma.compress(data, preset=9)
    if wrapper == "bz2":
        return "bz2", bz2.compress(data, compresslevel=9)
    if wrapper != "best":
        raise ValueError(f"Unknown wrapper: {wrapper}")
    options = [
        apply_wrapper(data, "none"),
        apply_wrapper(data, "zlib"),
        apply_wrapper(data, "lzma"),
        apply_wrapper(data, "bz2"),
    ]
    return min(options, key=lambda item: len(item[1]))


def remove_wrapper(data: bytes, wrapper: str) -> bytes:
    """Reverse a final entropy wrapper."""

    if wrapper == "none":
        return data
    if wrapper == "zlib":
        return zlib.decompress(data)
    if wrapper == "lzma":
        return lzma.decompress(data)
    if wrapper == "bz2":
        return bz2.decompress(data)
    raise ValueError(f"Unknown wrapper: {wrapper}")
