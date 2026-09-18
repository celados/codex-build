import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("manage-runner-cache.sh")


class RunnerCacheTest(unittest.TestCase):
    def test_failed_collector_discards_only_mbx(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "codex-build"
            for name in ("mbx", "cargo-home", "v8-cache", "target"):
                (cache / name).mkdir(parents=True)
                (cache / name / "keep").touch()
            executable = root / "mbx"
            executable.write_text("#!/bin/sh\nexit 1\n")
            executable.chmod(0o755)
            result = subprocess.run(
                ["bash", str(SCRIPT), "trim", directory],
                env={**os.environ, "PATH": f"{root}:{os.environ['PATH']}"},
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((cache / "mbx").exists())
            for name in ("cargo-home", "v8-cache", "target"):
                self.assertTrue((cache / name / "keep").exists())

    def test_rejects_broad_or_relative_roots(self):
        for root in ("/", "relative", ""):
            result = subprocess.run(
                ["bash", str(SCRIPT), "trim", root], capture_output=True
            )
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
