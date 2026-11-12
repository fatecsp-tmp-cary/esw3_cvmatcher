import hashlib
import json
from types import SimpleNamespace

import pytest

from src.extraction.gliner import (
    _POLICY,
    ARTIFACT_FILES,
    EXTRACTION_VERSION,
    LABELS,
    GlinerExtractor,
    bounded_chunks,
    file_hash,
    validate_artifacts,
)


def fake_extractor(predict):
    subject = object.__new__(GlinerExtractor)
    subject.model = SimpleNamespace(predict_entities=predict)
    subject._fits = lambda text: len(text) <= 100
    return subject


def test_bounded_chunks_cover_unicode_and_overlong_tokens_without_truncation():
    text = "🦉ação " * 300 + "x" * 400
    windows = bounded_chunks(text, lambda value: len(value) <= 45)
    assert windows[0].start == 0 and windows[-1].end == len(text)
    assert all(
        window.text == text[window.start : window.end] and len(window.text) <= 45
        for window in windows
    )
    assert all(
        left.end >= right.start and right.start > left.start
        for left, right in zip(windows, windows[1:], strict=False)
    )
    assert set().union(*(set(range(c.start, c.end)) for c in windows)) == set(range(len(text)))
    assert bounded_chunks("", lambda _: True) == ()
    with pytest.raises(ValueError):
        bounded_chunks("a", lambda _: False)


def test_offsets_overlap_dedup_and_unclassified_evidence():
    text = "a " * 42 + "Python" + " e " * 60

    def predict(chunk, labels, **kwargs):
        assert tuple(labels) == LABELS
        assert kwargs == {"threshold": 0.3, "flat_ner": False}
        offset = chunk.find("Python")
        if offset < 0:
            return []
        return [
            {"start": offset, "end": offset + 6, "label": "skill", "score": score, "text": "Python"}
            for score in (0.7, 0.9)
        ]

    result = fake_extractor(predict).extract(text)
    assert len(result) == 1
    span = result[0]
    assert text[span.start : span.end] == "Python"
    assert span.confidence == 0.9
    assert span.serialize(text)["requirement_class"] is None


@pytest.mark.parametrize(
    "entity",
    [
        {"start": 0, "end": 99, "label": "skill", "score": 0.8, "text": "Python"},
        {"start": 0, "end": 6, "label": "mandatory", "score": 0.8, "text": "Python"},
        {"start": 0, "end": 6, "label": "skill", "score": float("nan"), "text": "Python"},
        {"start": 0, "end": 6, "label": "skill", "score": 0.8, "text": "something else"},
        "raw malformed output",
    ],
)
def test_invalid_predictions_fail_closed(entity):
    with pytest.raises(ValueError):
        fake_extractor(lambda *args, **kwargs: [entity]).extract("Python")


def test_low_confidence_predictions_do_not_create_evidence():
    assert (
        fake_extractor(
            lambda *args, **kwargs: [
                {"start": 0, "end": 6, "label": "skill", "score": 0.1, "text": "Python"}
            ]
        ).extract("Python")
        == []
    )


def test_exact_tokenized_prompt_budget_and_word_limit():
    subject = object.__new__(GlinerExtractor)
    subject.model = SimpleNamespace(
        data_processor=SimpleNamespace(
            words_splitter=lambda value: [(word, 0, 1) for word in value.split()],
            prepare_inputs=lambda words, labels: ([list(labels) + words[0]], [len(labels)]),
        )
    )
    calls = []

    def tokenizer(inputs, **kwargs):
        calls.append(kwargs)
        return {"input_ids": [[0] * (10 + sum(len(word) for word in inputs[0]))]}

    subject.tokenizer = tokenizer
    assert subject._fits("Python")
    assert not subject._fits("x" * 500)
    assert not subject._fits("x " * 385)
    assert calls[0]["truncation"] is False and calls[0]["add_special_tokens"] is False


@pytest.fixture
def artifacts(tmp_path):
    for name in ARTIFACT_FILES:
        (tmp_path / name).write_bytes(b"synthetic artifact")
    backbone = {"model_type": "deberta-v2"}
    (tmp_path / "config.json").write_text(json.dumps(backbone))
    (tmp_path / "tokenizer_config.json").write_text("{}")
    (tmp_path / "gliner_config.json").write_text(
        json.dumps({"model_name": "microsoft/mdeberta-v3-base", "encoder_config": backbone})
    )
    manifest = {
        "policy": _POLICY,
        "files": {name: file_hash(tmp_path / name) for name in ARTIFACT_FILES},
    }
    (tmp_path / "provenance.json").write_text(json.dumps(manifest))
    return tmp_path


def test_artifact_integrity_and_pinned_policy(artifacts):
    assert validate_artifacts(artifacts) == artifacts
    assert EXTRACTION_VERSION.startswith("gliner-job-v1-")
    (artifacts / "model.safetensors").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash"):
        validate_artifacts(artifacts)


def test_backbone_cannot_silently_use_remote_main(artifacts):
    config = {"model_name": "unrelated/backbone", "encoder_config": {"model_type": "deberta-v2"}}
    (artifacts / "gliner_config.json").write_text(json.dumps(config))
    manifest = json.loads((artifacts / "provenance.json").read_text())
    manifest["files"]["gliner_config.json"] = hashlib.sha256(
        (artifacts / "gliner_config.json").read_bytes()
    ).hexdigest()
    (artifacts / "provenance.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unpinned"):
        validate_artifacts(artifacts)


def test_serving_loads_only_verified_local_artifacts(artifacts, monkeypatch):
    import sys

    monkeypatch.setattr(
        "src.extraction.gliner.version", lambda package: _POLICY["packages"][package]
    )

    calls = []
    tokenizer = SimpleNamespace(model_max_length=None)
    model = SimpleNamespace(
        data_processor=SimpleNamespace(transformer_tokenizer=tokenizer),
        eval=lambda: calls.append("eval"),
    )

    def load(directory, **kwargs):
        assert directory == str(artifacts)
        assert kwargs == {
            "local_files_only": True,
            "map_location": "cpu",
            "strict": True,
            "load_tokenizer": True,
            "low_cpu_mem_usage": True,
        }
        calls.append("local_load")
        return model

    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(set_num_threads=lambda value: calls.append(value))
    )
    monkeypatch.setitem(
        sys.modules, "gliner", SimpleNamespace(GLiNER=SimpleNamespace(from_pretrained=load))
    )
    subject = GlinerExtractor(artifacts)
    assert subject.model is model
    assert tokenizer.model_max_length == 384
    assert calls == [1, "local_load", "eval"]


def test_preparation_downloads_only_explicit_pins_and_is_idempotent(tmp_path, monkeypatch):
    import runpy
    import sys
    from pathlib import Path

    from src.extraction.gliner import MODEL_ID, MODEL_REVISION, TOKENIZER_ID, TOKENIZER_REVISION

    requests = []
    cache = tmp_path / "cache"
    cache.mkdir()

    def download(repo, filename, *, revision, token):
        requests.append((repo, filename, revision))
        assert token is False
        path = cache / (repo.replace("/", "-") + "-" + filename)
        if filename == "gliner_config.json":
            path.write_text(json.dumps({"model_name": TOKENIZER_ID}))
        elif filename == "config.json":
            path.write_text(json.dumps({"model_type": "deberta-v2"}))
        elif filename == "tokenizer_config.json":
            path.write_text("{}")
        else:
            path.write_bytes(b"synthetic model artifact")
        return path

    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(hf_hub_download=download))
    prepare = runpy.run_path(
        str(Path(__file__).parents[3] / "scripts/models/prepare_extraction.py")
    )["prepare"]
    destination = tmp_path / "prepared"
    assert prepare(destination) == destination
    assert requests == [
        (MODEL_ID, "gliner_config.json", MODEL_REVISION),
        (MODEL_ID, "model.safetensors", MODEL_REVISION),
        *[
            (TOKENIZER_ID, name, TOKENIZER_REVISION)
            for name in ("config.json", "tokenizer_config.json", "spm.model")
        ],
    ]
    assert prepare(destination) == destination and len(requests) == 5
    (destination / "spm.model").write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        prepare(destination)
    assert (destination / "spm.model").read_bytes() == b"corrupt"


def test_serving_rejects_inference_dependency_drift(artifacts, monkeypatch):
    monkeypatch.setattr("src.extraction.gliner.version", lambda package: "unexpected")
    with pytest.raises(ValueError, match="package version"):
        GlinerExtractor(artifacts)
