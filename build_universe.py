"""Build a coordinate universe JSON file from input data."""

from __future__ import annotations

import argparse
from pathlib import Path

from src import BuilderConfig, UniverseBuilder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", type=Path, required=True, help="Input files used to build the universe.")
    parser.add_argument("--out", type=Path, required=True, help="Output universe JSON path.")
    parser.add_argument("--max-layers", type=int, default=2, help="Maximum recursive coordinate layers.")
    parser.add_argument("--max-nodes-per-layer", type=int, default=4096, help="Maximum nodes kept in each layer.")
    parser.add_argument("--max-ngram", type=int, default=12, help="Maximum coordinate expansion length.")
    parser.add_argument("--min-count", type=int, default=3, help="Minimum candidate frequency.")
    parser.add_argument("--active-min-count", type=int, default=2, help="Minimum post-match active frequency.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    documents = [path.read_bytes() for path in args.input]
    config = BuilderConfig(
        max_layers=args.max_layers,
        max_nodes_per_layer=args.max_nodes_per_layer,
        max_ngram=args.max_ngram,
        min_count=args.min_count,
        active_min_count=args.active_min_count,
    )
    universe, report = UniverseBuilder(config).fit_bytes(documents)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    universe.save(args.out)

    print(f"Universe saved: {args.out}")
    print(f"Layers: {universe.layer_count}")
    print(f"Nodes: {universe.node_count:,}")
    print(f"Build symbol ratio: {report.ratio:.3f}")
    for layer in report.layer_reports:
        print(
            f"  layer {layer.layer}: nodes={layer.accepted_nodes:,} "
            f"ratio={layer.ratio:.3f} symbols={layer.input_symbols:,}->{layer.output_symbols:,}"
        )


if __name__ == "__main__":
    main()
