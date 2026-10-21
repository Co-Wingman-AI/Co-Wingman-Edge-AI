"""Repository tools must remain importable inside environments with other scripts packages."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ScriptImportTests(unittest.TestCase):
    def test_repository_tools_win_over_installed_scripts_package(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            # Simulate a dependency shipping its own regular `scripts` package
            # later on sys.path, as can happen in a populated speech environment.
            external = Path(directory) / "scripts"
            external.mkdir()
            (external / "__init__.py").write_text("", encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = directory + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; "
                    "from scripts import timing_report, navigator_benchmark, "
                    "token_benchmark, setup_s3_bucket; "
                    "assert all(Path(module.__file__).resolve().parent == "
                    "Path.cwd() / 'scripts' for module in "
                    "(timing_report, navigator_benchmark, token_benchmark, setup_s3_bucket))",
                ],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
