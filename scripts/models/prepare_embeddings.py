#!/usr/bin/env python3
"""Explicit pinned model preparation; never invoked by API/worker serving."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from huggingface_hub import snapshot_download

# Usable as a standalone script without installing the local project.
MODEL_ID = "intfloat/multilingual-e5-small"
REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    root = Path(
        snapshot_download(
            repo_id=MODEL_ID,
            revision=REVISION,
            cache_dir=args.cache_dir,
            token=False,
            allow_patterns=["*.json", "*.safetensors", "tokenizer.model", "*.txt", "1_Pooling/*"],
            ignore_patterns=["onnx/*", "openvino/*"],
        )
    )
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            with path.open("rb") as stream:
                files[str(path.relative_to(root))] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
    manifest = {"model": MODEL_ID, "revision": REVISION, "snapshot": str(root), "files": files}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared pinned model; hashed {len(files)} files; manifest: {args.manifest}")


if __name__ == "__main__":
    main()
