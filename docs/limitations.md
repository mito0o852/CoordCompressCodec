# Limitations

V1 is intentionally simple and honest.

- It is optimized for clarity, not maximum possible compression.
- The universe is external to DCC1 payloads. If you must store the universe with
  every small file, the total archive size can be worse than standard
  compressors.
- The current selector is frequency/profit based. More advanced held-out
  predictive selectors are future work.
- Byte-level tokens are universal and exact, but they may require more layers
  than a domain-specific tokenizer.
- Mature compressors such as lzma can still win on pure byte-size archiving.

The strength of this V1 is that it gives us a clean, testable base for future
coordinate-selection improvements.
