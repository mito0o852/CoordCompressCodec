# Mathematical Proof Of Losslessness

Let the original byte-token sequence be:

```text
S0 = [b1, b2, ..., bn]
```

Each coordinate node is a definition:

```text
c_i := [x1, x2, ..., xk]
```

where every `xj` is either a byte token or a coordinate from an earlier layer.

Encoding applies layer functions:

```text
S1 = F1(S0)
S2 = F2(S1)
...
Sm = Fm(Sm-1)
```

Each `Fi` replaces selected adjacent expansions with their coordinate ID. The
decoder stores the inverse definition:

```text
c_i -> [x1, x2, ..., xk]
```

Decoding applies recursive expansion in reverse until only byte IDs remain.
Because coordinate definitions are acyclic and exact, each replacement has one
unique inverse. Therefore:

```text
decode(encode(S0)) = S0
```

The implementation additionally verifies the SHA-256 checksum of reconstructed
bytes when decoding payloads.
