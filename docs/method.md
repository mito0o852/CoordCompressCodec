# Method

CoordCompressCodec builds a shared coordinate universe from recurring byte
sequences.

1. Convert input bytes to base IDs `0..255`.
2. Count repeated n-grams.
3. Select profitable repeated sequences as coordinate nodes.
4. Greedily replace matching sequences with coordinate IDs.
5. Repeat the process for additional layers.
6. Store the final symbol stream in a DCC1 payload.

The important design decision is that every coordinate node is reversible:

```text
C300 -> [72, 101, 108, 108, 111]
```

Layer 2 can reference layer 1:

```text
C900 -> [C300, 32, C301]
```

During decoding, coordinates are expanded recursively until only byte IDs
remain.
