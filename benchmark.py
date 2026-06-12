"""Benchmark coordinate compression against common standard compressors."""

from __future__ import annotations

import argparse
from pathlib import Path

from src import BuilderConfig
from src.benchmark import benchmark_documents, read_files
from src.metrics import format_table, metrics_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", type=Path, required=True, help="Input files to benchmark.")
    parser.add_argument("--save-universe", type=Path, default=None, help="Optional path to save the built universe.")
    parser.add_argument("--max-layers", type=int, default=2)
    parser.add_argument("--max-nodes-per-layer", type=int, default=4096)
    parser.add_argument("--max-ngram", type=int, default=12)
    parser.add_argument("--min-count", type=int, default=3)
    parser.add_argument("--active-min-count", type=int, default=2)
    parser.add_argument(
        "--wrapper",
        choices=("none", "zlib", "lzma", "bz2", "best"),
        default="best",
        help="Final wrapper used for DCC1 payload bytes.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    documents, names = read_files(args.input)
    config = BuilderConfig(
        max_layers=args.max_layers,
        max_nodes_per_layer=args.max_nodes_per_layer,
        max_ngram=args.max_ngram,
        min_count=args.min_count,
        active_min_count=args.active_min_count,
    )
    universe, metrics = benchmark_documents(documents, names=names, config=config, wrapper=args.wrapper)
    if args.save_universe is not None:
        args.save_universe.parent.mkdir(parents=True, exist_ok=True)
        universe.save(args.save_universe)

    headers = [
        "file",
        "before bytes",
        "after symbols",
        "symbol ratio",
        "payload bytes",
        "payload ratio",
        "best std bytes",
        "best std ratio",
        "roundtrip",
    ]
    print(format_table(headers, metrics_rows(metrics)))
    print()
    print(f"Universe layers: {universe.layer_count}")
    print(f"Universe nodes: {universe.node_count:,}")
    print(f"Universe hash: {universe.fingerprint()[:16]}...")


if __name__ == "__main__":
    main()
