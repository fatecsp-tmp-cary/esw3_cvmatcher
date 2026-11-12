#!/usr/bin/env python3
"""Explicit pinned local artifact acquisition; no model inference or package installation."""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.extraction.gliner import (  # noqa: E402
    _POLICY,
    ARTIFACT_FILES,
    MODEL_ID,
    MODEL_REVISION,
    TOKENIZER_ID,
    TOKENIZER_REVISION,
    file_hash,
    validate_artifacts,
)


def prepare(destination: Path) -> Path:
    from huggingface_hub import hf_hub_download

    destination = destination.resolve()
    if destination.exists():
        return validate_artifacts(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
    for repo, revision, filename, output in [
        (MODEL_ID, MODEL_REVISION, "gliner_config.json", "gliner_config.upstream.json"),
        (MODEL_ID, MODEL_REVISION, "model.safetensors", "model.safetensors"),
        *[
            (TOKENIZER_ID, TOKENIZER_REVISION, name, name)
            for name in ("config.json", "tokenizer_config.json", "spm.model")
        ],
    ]:
        cached = hf_hub_download(repo, filename, revision=revision, token=False)
        shutil.copyfile(cached, stage / output)
    config = json.loads((stage / "gliner_config.upstream.json").read_text())
    # Embed the exact pinned backbone configuration. GLiNER then needs neither
    # AutoConfig(main) nor pretrained backbone weights; the NER safetensors carry weights.
    config["encoder_config"] = json.loads((stage / "config.json").read_text())
    (stage / "gliner_config.json").write_text(json.dumps(config, sort_keys=True, indent=2) + "\n")
    manifest = {
        "policy": _POLICY,
        "files": {name: file_hash(stage / name) for name in sorted(ARTIFACT_FILES)},
        "sources": [
            {"repository": MODEL_ID, "revision": MODEL_REVISION},
            {"repository": TOKENIZER_ID, "revision": TOKENIZER_REVISION},
        ],
    }
    (stage / "provenance.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    validate_artifacts(stage)
    stage.rename(destination)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    print(prepare(parser.parse_args().destination))
