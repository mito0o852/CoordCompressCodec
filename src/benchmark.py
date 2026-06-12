"""Benchmark helpers for coordinate compression."""

from __future__ import annotations

import bz2
import lzma
from pathlib import Path
import zlib
from typing import Sequence

from .builder import BuilderConfig, UniverseBuilder
from .codec import DcDecoder, DcEncoder
from .file_format import Wrapper, pack_payload
from .metrics import CompressionMetrics
from .universe import CoordinateUniverse


def benchmark_documents(
    documents: Sequence[bytes],
    *,
    names: Sequence[str] | None = None,
    config: BuilderConfig | None = None,
    wrapper: Wrapper = "best",
) -> tuple[CoordinateUniverse, list[CompressionMetrics]]:
    """Build a universe and benchmark it on byte documents.

    Args:
        documents: Byte documents used for both universe construction and
            evaluation. This measures shared-universe compression.
        names: Optional display names for documents.
        config: Universe build configuration.
        wrapper: Final DCC1 payload wrapper.

    Returns:
        ``(universe, metrics)``.
    """

    builder = UniverseBuilder(config)
    universe, _ = builder.fit_bytes(documents)
    metrics = evaluate_documents(documents, universe=universe, names=names, wrapper=wrapper)
    return universe, metrics


def evaluate_documents(
    documents: Sequence[bytes],
    *,
    universe: CoordinateUniverse,
    names: Sequence[str] | None = None,
    wrapper: Wrapper = "best",
) -> list[CompressionMetrics]:
    """Evaluate an existing universe on byte documents.

    Args:
        documents: Evaluation documents.
        universe: Coordinate universe used to encode/decode the documents.
        names: Optional row names.
        wrapper: Final DCC1 payload wrapper.

    Returns:
        Per-document metrics.
    """

    encoder = DcEncoder(universe)
    decoder = DcDecoder(universe)
    rows: list[CompressionMetrics] = []
    row_names = list(names or [f"document_{index}" for index in range(len(documents))])
    for name, data in zip(row_names, documents):
        payload = encoder.encode_bytes(data)
        archive = pack_payload(payload, universe=universe, wrapper=wrapper)
        restored = decoder.decode_to_bytes(payload)
        rows.append(
            CompressionMetrics(
                name=name,
                original_bytes=len(data),
                coordinate_symbols=payload.symbol_count,
                archive_bytes=len(archive),
                zlib_bytes=len(zlib.compress(data, level=9)),
                lzma_bytes=len(lzma.compress(data, preset=9)),
                bz2_bytes=len(bz2.compress(data, compresslevel=9)),
                roundtrip=restored == data,
            )
        )
    return rows


def read_files(paths: Sequence[Path]) -> tuple[list[bytes], list[str]]:
    """Read input files for benchmarking."""

    documents = [path.read_bytes() for path in paths]
    names = [path.name for path in paths]
    return documents, names
