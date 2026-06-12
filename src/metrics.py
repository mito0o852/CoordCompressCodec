"""Metrics and table helpers for coordinate compression."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class CompressionMetrics:
    """Compression metrics for one encoded input.

    Args:
        name: Human-readable row name.
        original_bytes: Original input size.
        coordinate_symbols: Number of symbols after coordinate encoding.
        archive_bytes: Serialized DCC1 payload size.
        zlib_bytes: Size of zlib-compressed original bytes.
        lzma_bytes: Size of lzma-compressed original bytes.
        bz2_bytes: Size of bz2-compressed original bytes.
        roundtrip: Whether decode reconstructed the exact original bytes.
    """

    name: str
    original_bytes: int
    coordinate_symbols: int
    archive_bytes: int
    zlib_bytes: int
    lzma_bytes: int
    bz2_bytes: int
    roundtrip: bool

    @property
    def symbol_ratio(self) -> float:
        """Coordinate symbols divided by original bytes."""

        return self.coordinate_symbols / max(1, self.original_bytes)

    @property
    def archive_ratio(self) -> float:
        """DCC1 archive bytes divided by original bytes."""

        return self.archive_bytes / max(1, self.original_bytes)

    @property
    def best_standard_ratio(self) -> float:
        """Best standard compressor ratio among zlib, lzma, and bz2."""

        return min(self.zlib_bytes, self.lzma_bytes, self.bz2_bytes) / max(1, self.original_bytes)


def format_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """Format a simple left-aligned text table."""

    string_rows = [[str(item) for item in row] for row in rows]
    widths = [
        max(len(str(header)), *(len(row[index]) for row in string_rows))
        for index, header in enumerate(headers)
    ]
    lines = [
        " | ".join(str(header).ljust(widths[index]) for index, header in enumerate(headers)),
        "-+-".join("-" * width for width in widths),
    ]
    for row in string_rows:
        lines.append(" | ".join(row[index].ljust(widths[index]) for index in range(len(headers))))
    return "\n".join(lines)


def metrics_rows(metrics: Sequence[CompressionMetrics]) -> list[tuple[str, str, str, str, str, str, str, str, str]]:
    """Convert compression metrics into printable table rows."""

    rows = []
    for item in metrics:
        best_standard = min(item.zlib_bytes, item.lzma_bytes, item.bz2_bytes)
        rows.append(
            (
                item.name,
                f"{item.original_bytes:,}",
                f"{item.coordinate_symbols:,}",
                f"{item.symbol_ratio:.3f}",
                f"{item.archive_bytes:,}",
                f"{item.archive_ratio:.3f}",
                f"{best_standard:,}",
                f"{item.best_standard_ratio:.3f}",
                "yes" if item.roundtrip else "no",
            )
        )
    return rows
