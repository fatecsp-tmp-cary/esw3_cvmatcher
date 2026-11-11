"""Pinned, offline local GLiNER job extraction; model labels are never requirements."""

import hashlib
import json
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path

from src.extraction.contracts import SpanEvidence, TextChunk

MODEL_ID = "urchade/gliner_multi-v2.1"
MODEL_REVISION = "443d26d654e0324125a96bebd8e796c14ff2efe6"
TOKENIZER_ID = "microsoft/mdeberta-v3-base"
TOKENIZER_REVISION = "a0484667b22365f84929a935b5e50a51f71f159d"
LABELS = (
    "skill",
    "tool",
    "framework",
    "database",
    "cloud",
    "education",
    "work experience requirement",
)
THRESHOLD = 0.3
MAX_TOKENS = 384
MAX_CHARACTERS = 1200
OVERLAP_CHARACTERS = 200
INFERENCE_PACKAGES = {"gliner": "0.2.30", "transformers": "4.57.6", "torch": "2.9.1+cpu"}
_POLICY: dict[str, object] = {
    "model": MODEL_ID,
    "model_revision": MODEL_REVISION,
    "tokenizer": TOKENIZER_ID,
    "tokenizer_revision": TOKENIZER_REVISION,
    "labels": LABELS,
    "threshold": THRESHOLD,
    "max_tokens": MAX_TOKENS,
    "max_characters": MAX_CHARACTERS,
    "overlap_characters": OVERLAP_CHARACTERS,
    "dedup": "same-label-overlap-confidence-length-offset-v1",
    "mandatory_classification": False,
    "packages": INFERENCE_PACKAGES,
}
EXTRACTION_VERSION = (
    "gliner-job-v1-" + hashlib.sha256(json.dumps(_POLICY, sort_keys=True).encode()).hexdigest()[:24]
)
ARTIFACT_FILES = frozenset(
    {
        "model.safetensors",
        "gliner_config.json",
        "gliner_config.upstream.json",
        "config.json",
        "tokenizer_config.json",
        "spm.model",
    }
)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_artifacts(directory: str | Path) -> Path:
    """Reject incomplete/mismatched artifacts before loading any model code."""
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "provenance.json").read_text())
    if manifest.get("policy") != json.loads(json.dumps(_POLICY)):
        raise ValueError("Extraction artifact policy mismatch")
    hashes = manifest.get("files", {})
    if set(hashes) != ARTIFACT_FILES:
        raise ValueError("Incomplete extraction artifacts")
    for filename, expected in hashes.items():
        path = directory / filename
        if path.is_symlink() or not path.is_file() or file_hash(path) != expected:
            raise ValueError("Extraction artifact hash mismatch")
    config = json.loads((directory / "gliner_config.json").read_text())
    backbone = json.loads((directory / "config.json").read_text())
    tokenizer = json.loads((directory / "tokenizer_config.json").read_text())
    if (
        config.get("model_name") != TOKENIZER_ID
        or config.get("encoder_config") != backbone
        or any("auto_map" in item for item in (config, backbone, tokenizer))
    ):
        raise ValueError("Unpinned or unsupported local model configuration")
    return directory


def bounded_chunks(text: str, fits: Callable[[str], bool]) -> tuple[TextChunk, ...]:
    """Cover every character, reducing windows until exact model-token budget fits."""
    output = []
    start = 0
    while start < len(text):
        low, high, best = start + 1, min(start + MAX_CHARACTERS, len(text)), start
        while low <= high:
            end = (low + high) // 2
            if fits(text[start:end]):
                best, low = end, end + 1
            else:
                high = end - 1
        if best == start:
            raise ValueError("Extraction token budget cannot cover input")
        # Token counts are not strictly monotonic over character prefixes.
        # Revalidate the chosen prefix; fit is never assumed from character length.
        if not fits(text[start:best]):
            raise ValueError("Extraction chunk exceeds model token budget")
        output.append(TextChunk(start, best, text[start:best]))
        if best == len(text):
            break
        start = best - min(OVERLAP_CHARACTERS, (best - start) // 4)
    return tuple(output)


class GlinerExtractor:
    def __init__(self, model_directory: str | Path):
        directory = validate_artifacts(model_directory)
        if any(version(package) != expected for package, expected in INFERENCE_PACKAGES.items()):
            raise ValueError("Extraction inference package version mismatch")
        # Imports are lazy: normal CI uses an injected backend without downloading/loading models.
        import torch
        from gliner import GLiNER

        torch.set_num_threads(1)
        self.model = GLiNER.from_pretrained(
            str(directory),
            local_files_only=True,
            map_location="cpu",
            strict=True,
            load_tokenizer=True,
            low_cpu_mem_usage=True,
        )
        self.model.eval()
        self.tokenizer = self.model.data_processor.transformer_tokenizer
        self.tokenizer.model_max_length = MAX_TOKENS

    def _fits(self, text: str) -> bool:
        processor = self.model.data_processor
        words = [value[0] for value in processor.words_splitter(text)]
        if len(words) > MAX_TOKENS:
            return False
        inputs, _ = processor.prepare_inputs([words], list(LABELS))
        encoded = self.tokenizer(
            inputs,
            is_split_into_words=True,
            add_special_tokens=False,
            truncation=False,
            padding=False,
        )
        return len(encoded["input_ids"][0]) <= MAX_TOKENS

    def extract(self, text: str) -> list[SpanEvidence]:
        if not isinstance(text, str):
            raise TypeError("Job extraction requires cleaned text")
        predictions = []
        for chunk in bounded_chunks(text, self._fits):
            if not chunk.text.strip():
                continue
            entities = self.model.predict_entities(
                chunk.text, list(LABELS), threshold=THRESHOLD, flat_ner=False
            )
            if not isinstance(entities, list):
                raise ValueError("Invalid local extraction predictions")
            for entity in entities:
                if not isinstance(entity, dict):
                    raise ValueError("Invalid local extraction prediction")
                local = SpanEvidence(
                    entity.get("start"), entity.get("end"), entity.get("label"), entity.get("score")
                )
                local.serialize(chunk.text)
                if (
                    local.label not in LABELS
                    or entity.get("text") != chunk.text[local.start : local.end]
                ):
                    raise ValueError("Invalid local extraction evidence")
                if local.confidence < THRESHOLD:
                    continue
                predictions.append(
                    SpanEvidence(
                        chunk.start + local.start,
                        chunk.start + local.end,
                        local.label,
                        local.confidence,
                    )
                )
        # Resolve same-label overlapping windows deterministically, preserving strongest evidence.
        selected = []
        for span in sorted(
            predictions, key=lambda s: (-s.confidence, -(s.end - s.start), s.start, s.label)
        ):
            if not any(
                span.label == old.label and span.start < old.end and old.start < span.end
                for old in selected
            ):
                selected.append(span)
        return sorted(selected, key=lambda s: (s.start, s.end, s.label))


# Compatibility with the spelling in the initial integration assignment.
GlainerExtractor = GlinerExtractor
