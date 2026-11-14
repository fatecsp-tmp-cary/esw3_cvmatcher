"""Preparation configures hub telemetry before the hub module initializes."""

import builtins
import json
import os
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

from src.embeddings.config import MODEL_ID, MODEL_REVISION


def test_telemetry_is_configured_before_importing_hub(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_HUB_DISABLE_TELEMETRY", "temporary-test-value")
    monkeypatch.delenv("HF_HUB_DISABLE_TELEMETRY")
    root = tmp_path / "snapshot"
    root.mkdir()
    manifest = tmp_path / "manifest.json"
    called = []
    real_import = builtins.__import__

    def import_module(name, *args, **kwargs):
        if name == "huggingface_hub":
            assert os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"

            def download(**options):
                called.append(options)
                return str(root)

            return SimpleNamespace(snapshot_download=download)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_module)
    monkeypatch.setattr(sys, "argv", ["prepare_embeddings.py", "--manifest", str(manifest)])
    script = Path(__file__).parents[3] / "scripts/models/prepare_embeddings.py"
    runpy.run_path(str(script), run_name="__main__")
    assert called[0]["repo_id"] == MODEL_ID and called[0]["revision"] == MODEL_REVISION
    assert called[0]["token"] is False
    assert json.loads(manifest.read_text())["files"] == {}
