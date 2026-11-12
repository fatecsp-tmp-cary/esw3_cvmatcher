"""Offline regressions for the lock consistency gate (no package resolution)."""

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("lock_inputs", Path(__file__).with_name("inputs.py"))
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LockConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "requirements").mkdir()
        (self.root / "pyproject.toml").write_text((MODULE.ROOT / "pyproject.toml").read_text())
        self.addCleanup(patch.stopall)
        patch.object(MODULE, "ROOT", self.root).start()
        self.invoke()
        for name in MODULE.inputs():
            lock = name.replace(".in", ".lock")
            (self.root / "requirements" / lock).write_text(
                (Path(__file__).resolve().parents[2] / "requirements" / lock).read_text()
            )
        self.invoke("--record")

    def invoke(self, *arguments):
        with patch.object(sys, "argv", ["inputs.py", *arguments]):
            MODULE.main()

    def test_generated_artifacts_pass(self):
        self.invoke("--check")

    def test_pyproject_drift_fails(self):
        path = self.root / "pyproject.toml"
        path.write_text(path.read_text().replace("fastapi>=0.115", "fastapi>=0.116"))
        with self.assertRaisesRegex(SystemExit, "Stale lock input"):
            self.invoke("--check")

    def test_hash_drift_fails(self):
        path = self.root / "requirements/runtime.lock"
        path.write_text(
            re.sub(r"sha256:[a-f0-9]{64}", "sha256:" + "b" * 64, path.read_text(), count=1)
        )
        with self.assertRaisesRegex(SystemExit, "provenance differs"):
            self.invoke("--check")

    def test_unhashed_lock_cannot_be_recorded(self):
        (self.root / "requirements/runtime.lock").write_text("example==1.0\n")
        with self.assertRaisesRegex(SystemExit, "Unhashed"):
            self.invoke("--record")

    def test_missing_pair_fails(self):
        (self.root / "requirements/dev.lock").unlink()
        with self.assertRaisesRegex(SystemExit, "five input/lock pairs"):
            self.invoke("--check")

    def test_wrong_direct_pin_cannot_be_recorded(self):
        path = self.root / "requirements/local-models.lock"
        path.write_text(path.read_text().replace("torch==2.9.1+cpu", "torch==2.9.0+cpu"))
        with self.assertRaisesRegex(SystemExit, "Direct requirement differs"):
            self.invoke("--record")

    def test_wrong_target_fails(self):
        path = self.root / "requirements/provenance.json"
        manifest = json.loads(path.read_text())
        manifest["python"] = "3.13"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(SystemExit, "Unexpected lock target"):
            self.invoke("--check")

    def test_build_constraint_conflict_cannot_be_recorded(self):
        path = self.root / "requirements/local-models.lock"
        path.write_text(path.read_text().replace("setuptools==78.1.0", "setuptools==78.2.0"))
        with self.assertRaisesRegex(SystemExit, "Referenced dependency versions differ"):
            self.invoke("--record")

    def test_include_missing_package_cannot_be_recorded(self):
        path = self.root / "requirements/dev.lock"
        content = re.sub(r"\\\n\s*", " ", path.read_text())
        path.write_text(
            "\n".join(line for line in content.splitlines() if not line.startswith("h11=="))
        )
        with self.assertRaisesRegex(SystemExit, "Referenced dependency versions differ"):
            self.invoke("--record")

    def test_combined_environment_conflict_cannot_be_recorded(self):
        # A shared transitive package outside runtime/build still must agree.
        for name, version in (("dev.lock", "1.0"), ("local-models.lock", "2.0")):
            path = self.root / "requirements" / name
            entry = f"review-probe=={version} --hash=sha256:{'a' * 64}\n"
            path.write_text(path.read_text() + "\n" + entry)
        with self.assertRaisesRegex(SystemExit, "Development and local-model"):
            self.invoke("--record")


if __name__ == "__main__":
    unittest.main()
