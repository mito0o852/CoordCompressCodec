"""Encode a file into a DCC1 coordinate payload."""

from __future__ import annotations

import argparse
from pathlib import Path

from src import CoordinateUniverse, DcEncoder
from src.file_format import pack_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Input file to encode.")
    parser.add_argument("--universe", type=Path, required=True, help="Coordinate universe JSON file.")
    parser.add_argument("--out", type=Path, required=True, help="Output .dcc payload file.")
    parser.add_argument(
        "--wrapper",
        choices=("none", "zlib", "lzma", "bz2", "best"),
        default="best",
        help="Final entropy wrapper for the encoded symbol stream.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    universe = CoordinateUniverse.load(args.universe)
    data = args.input.read_bytes()
    payload = DcEncoder(universe).encode_bytes(data)
    archive = pack_payload(payload, universe=universe, wrapper=args.wrapper)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(archive)

    print(f"Encoded: {args.input} -> {args.out}")
    print(f"Original bytes: {len(data):,}")
    print(f"Coordinate symbols: {payload.symbol_count:,}")
    print(f"Symbol ratio: {payload.symbol_ratio:.3f}")
    print(f"Payload bytes: {len(archive):,}")
    print(f"Payload ratio: {len(archive) / max(1, len(data)):.3f}")
    print(f"Preview: {payload.preview()}")


if __name__ == "__main__":
    main()
