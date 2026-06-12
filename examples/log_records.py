"""Structured text API example for CoordCompressCodec."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import BuilderConfig, DcDecoder, DcEncoder, UniverseBuilder


text = """\
127.0.0.1 - - [10/Oct/2026:13:55:36 +0000] "GET /api/users HTTP/1.1" 200 512
127.0.0.1 - - [10/Oct/2026:13:55:37 +0000] "GET /api/orders HTTP/1.1" 200 768
127.0.0.1 - - [10/Oct/2026:13:55:38 +0000] "POST /api/orders HTTP/1.1" 201 128
127.0.0.1 - - [10/Oct/2026:13:55:39 +0000] "GET /api/users HTTP/1.1" 200 512
127.0.0.1 - - [10/Oct/2026:13:55:40 +0000] "GET /api/orders HTTP/1.1" 200 768
127.0.0.1 - - [10/Oct/2026:13:55:41 +0000] "POST /api/users HTTP/1.1" 201 128
"""

config = BuilderConfig(max_layers=2, max_nodes_per_layer=256, max_ngram=16)
universe, report = UniverseBuilder(config).fit_text(text)
payload = DcEncoder(universe).encode(text)
decoded = DcDecoder(universe).decode(payload)

print("preview:", payload.preview())
print("symbol_ratio:", round(payload.symbol_ratio, 3))
print("build_ratio:", round(report.ratio, 3))
print("nodes:", universe.node_count)
print("roundtrip:", decoded == text)
