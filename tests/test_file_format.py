from __future__ import annotations

import unittest

from src import DcDecoder, DcEncoder, UniverseBuilder
from src.file_format import pack_payload, unpack_payload


class FileFormatTests(unittest.TestCase):
    def test_payload_pack_unpack_roundtrip(self) -> None:
        data = b"red blue red blue red blue\n" * 5
        universe, _ = UniverseBuilder().fit_bytes([data])
        payload = DcEncoder(universe).encode_bytes(data)

        archive = pack_payload(payload, universe=universe, wrapper="best")
        parsed = unpack_payload(archive, universe=universe)
        restored = DcDecoder(universe).decode_to_bytes(parsed)

        self.assertEqual(restored, data)

    def test_wrong_universe_is_rejected(self) -> None:
        data = b"one two one two one two\n"
        universe, _ = UniverseBuilder().fit_bytes([data])
        other_universe, _ = UniverseBuilder().fit_bytes([b"abc abc abc abc\n"])
        payload = DcEncoder(universe).encode_bytes(data)
        archive = pack_payload(payload, universe=universe)

        with self.assertRaises(ValueError):
            unpack_payload(archive, universe=other_universe)


if __name__ == "__main__":
    unittest.main()
