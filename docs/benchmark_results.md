# Benchmark Results

Run from the `CoordCompressCodec/` repository root:

```bash
python benchmark.py \
  --input ../sample_data/alice.txt ../sample_data/apache_logs ../sample_data/posts.json ../sample_data/iris.csv ../sample_data/flights.csv \
  --save-universe artifacts/sample_universe.json \
  --max-layers 2 \
  --max-nodes-per-layer 12000 \
  --max-ngram 12 \
  --min-count 3 \
  --active-min-count 2
```

Result:

```text
file        | before bytes | after symbols | symbol ratio | payload bytes | payload ratio | best std bytes | best std ratio | roundtrip
------------+--------------+---------------+--------------+---------------+---------------+----------------+----------------+----------
alice.txt   | 174,314      | 80,263        | 0.460        | 56,012        | 0.321         | 49,017         | 0.281          | yes
apache_logs | 2,368,364    | 239,931       | 0.101        | 138,157       | 0.058         | 129,257        | 0.055          | yes
posts.json  | 27,520       | 11,678        | 0.424        | 6,681         | 0.243         | 5,077          | 0.184          | yes
iris.csv    | 3,858        | 1,853         | 0.480        | 1,028         | 0.266         | 662            | 0.172          | yes
flights.csv | 2,350        | 1,584         | 0.674        | 1,028         | 0.437         | 619            | 0.263          | yes
```

Universe:

```text
layers: 2
nodes: 4,674
hash: e3e771b0f1aae58d...
```

The key columns are:

- `before bytes`: original input size
- `after symbols`: coordinate stream length
- `symbol ratio`: coordinate symbols divided by original bytes
- `payload bytes`: serialized DCC1 payload size with shared universe
- `payload ratio`: DCC1 bytes divided by original bytes
- `best std bytes`: best result among zlib, lzma, and bz2 on the original bytes
- `roundtrip`: exact decode success
