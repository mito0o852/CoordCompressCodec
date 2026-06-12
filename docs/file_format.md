# DCC1 File Format

DCC1 stores an encoded coordinate stream. It does not store the coordinate
universe itself. Decoding requires the matching universe JSON file.

```text
4 bytes   magic: DCC1
4 bytes   big-endian JSON header length
N bytes   JSON header
M bytes   encoded varint body, optionally wrapped
```

Header fields:

```json
{
  "version": 1,
  "wrapper": "zlib",
  "original_size": 1234,
  "checksum": "...sha256...",
  "symbol_count": 567,
  "universe_hash": "...sha256..."
}
```

Wrappers:

- `none`
- `zlib`
- `lzma`
- `bz2`
- `best`

`best` tries all supported wrappers and stores the smallest body.
