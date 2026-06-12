from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from src import CoordinateUniverse, UniverseBuilder


class UniverseTests(unittest.TestCase):
    def test_save_load_keeps_encoding(self) -> None:
        text = b"alpha beta alpha beta alpha beta\n"
        universe, _ = UniverseBuilder().fit_bytes([text])

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "universe.json"
            universe.save(path)
            loaded = CoordinateUniverse.load(path)

        self.assertEqual(loaded.fingerprint(), universe.fingerprint())
        self.assertEqual(loaded.decode(loaded.encode(list(text))), list(text))

    def test_empty_universe_is_passthrough(self) -> None:
        universe = CoordinateUniverse.empty()
        tokens = [1, 2, 3, 255]
        self.assertEqual(universe.encode(tokens), tokens)
        self.assertEqual(universe.decode(tokens), tokens)


if __name__ == "__main__":
    unittest.main()
