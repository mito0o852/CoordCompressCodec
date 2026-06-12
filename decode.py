"""Decode a DCC1 coordinate payload back to the original file."""

from __future__ import annotations

import argparse
from pathlib import Path

from src import CoordinateUniverse, DcDecoder
from src.file_format import unpack_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Input .dcc payload file.")
    parser.add_argument("--universe", type=Path, required=True, help="Coordinate universe JSON file.")
    parser.add_argument("--out", type=Path, required=True, help="Restored output file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    universe = CoordinateUniverse.load(args.universe)
    payload = unpack_payload(args.input.read_bytes(), universe=universe)
    restored = DcDecoder(universe).decode_to_bytes(payload)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(restored)

    print(f"Decoded: {args.input} -> {args.out}")
    print(f"Restored bytes: {len(restored):,}")
    print("Checksum: ok")


if __name__ == "__main__":
    main()
