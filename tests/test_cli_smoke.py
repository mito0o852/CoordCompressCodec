from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliSmokeTests(unittest.TestCase):
    def test_build_encode_decode_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            source = work / "input.txt"
            universe = work / "universe.json"
            encoded = work / "payload.dcc"
            restored = work / "restored.txt"
            source.write_text("hello hello hello\nworld world world\n", encoding="utf-8")

            subprocess.run(
                [sys.executable, "build_universe.py", "--input", str(source), "--out", str(universe)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                [sys.executable, "encode.py", "--input", str(source), "--universe", str(universe), "--out", str(encoded)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            subprocess.run(
                [sys.executable, "decode.py", "--input", str(encoded), "--universe", str(universe), "--out", str(restored)],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(restored.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
