from __future__ import annotations

import unittest

from src import DcDecoder, DcEncoder, UniverseBuilder


class RoundtripTests(unittest.TestCase):
    def test_text_roundtrip(self) -> None:
        text = "This is a test. This is a test. This is only a test.\n"
        universe, _ = UniverseBuilder().fit_text(text)
        payload = DcEncoder(universe).encode(text)
        decoded = DcDecoder(universe).decode(payload)
        self.assertEqual(decoded, text)
        self.assertLess(payload.symbol_count, len(text.encode("utf-8")))

    def test_binary_roundtrip(self) -> None:
        data = (bytes(range(256)) + b"ABCABCABCABC") * 3
        universe, _ = UniverseBuilder().fit_bytes([data])
        payload = DcEncoder(universe).encode_bytes(data)
        decoded = DcDecoder(universe).decode_to_bytes(payload)
        self.assertEqual(decoded, data)


if __name__ == "__main__":
    unittest.main()
