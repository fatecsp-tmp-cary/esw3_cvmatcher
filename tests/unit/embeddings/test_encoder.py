import math

import pytest

from src.embeddings.config import DIMENSIONS, EmbeddingConfig
from src.embeddings.encoder import LocalEmbeddingEncoder, normalized_vector


class Tokenizer:
    def __init__(self):
        self.batches = []

    def __call__(self, text, **kwargs):
        assert kwargs == {"add_special_tokens": False, "truncation": False, "verbose": False}
        return {"input_ids": [ord(character) for character in text]}

    def num_special_tokens_to_add(self, pair=False):
        return 2

    def prepare_for_model(self, ids, **kwargs):
        assert kwargs["truncation"] is False
        return {"input_ids": [1, *ids, 2], "attention_mask": [1] * (len(ids) + 2)}

    def pad(self, features, padding, return_tensors):
        import torch

        self.batches.append([list(feature["input_ids"]) for feature in features])
        longest = max(len(feature["input_ids"]) for feature in features)
        return {
            key: torch.tensor(
                [feature[key] + [0] * (longest - len(feature[key])) for feature in features]
            )
            for key in ("input_ids", "attention_mask")
        }


class Model:
    max_seq_length = 64

    def __init__(self):
        self.tokenizer = Tokenizer()
        self.training = True
        self.device = None

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        self.training = False

    def __call__(self, features):
        import torch

        assert torch.is_inference_mode_enabled()
        values = features["input_ids"].sum(dim=1).float()
        vectors = torch.zeros((len(values), DIMENSIONS))
        vectors[:, 0] = values
        vectors[:, 1] = 1
        return {"sentence_embedding": vectors}


def test_full_token_coverage_prefixes_batches_cpu_eval_and_normalized_vectors():
    model = Model()
    encoder = LocalEmbeddingEncoder(
        EmbeddingConfig(max_tokens=40, overlap_tokens=4, batch_size=2), model=model
    )
    text = "".join(chr(index) for index in range(200, 350))
    result = encoder.encode_queries([text])
    assert len(result) == 1 and len(result[0]) == DIMENSIONS
    assert math.isclose(sum(value * value for value in result[0]), 1.0, abs_tol=1e-12)
    windows = [window for batch in model.tokenizer.batches for window in batch]
    assert all(len(batch) <= 2 for batch in model.tokenizer.batches)
    assert all(len(window) <= 40 for window in windows)
    prefix = [ord(char) for char in "query: "]
    assert all(window[1 : 1 + len(prefix)] == prefix for window in windows)
    covered = {token for window in windows for token in window if token >= 200}
    assert covered == set(range(200, 350))
    assert model.device == "cpu" and model.training is False
    # No retention of candidate texts or embeddings on the encoder.
    assert set(vars(encoder)) == {"config", "_model", "_lock"}
    model.tokenizer.batches.clear()
    encoder.encode_jobs(["Job"])
    assert model.tokenizer.batches[0][0][1:10] == [ord(char) for char in "passage: "]


def test_same_input_deterministic_and_no_empty_invented_evidence():
    encoder = LocalEmbeddingEncoder(EmbeddingConfig(overlap_tokens=4), model=Model())
    assert encoder.encode_queries(["Python"]) == encoder.encode_queries(["Python"])
    assert encoder.encode_queries([]) == []
    for texts in ([""], ["  "], "private", [None]):
        with pytest.raises(ValueError):
            encoder.encode_queries(texts)


@pytest.mark.parametrize("values", [[], [0.0] * 384, [float("nan")] * 384, [float("inf")] * 384])
def test_invalid_vectors_are_rejected(values):
    with pytest.raises(ValueError):
        normalized_vector(values)


def test_normalization_is_stable_for_extreme_finite_values():
    values = [1e308] * 384
    normalized = normalized_vector(values)
    assert all(math.isfinite(value) for value in normalized)
    assert math.isclose(sum(value * value for value in normalized), 1.0, abs_tol=1e-12)


def test_policy_identity_changes_on_window_policy_not_cache_or_batch():
    default = EmbeddingConfig()
    assert (
        default.model_version
        == EmbeddingConfig(cache_directory="/tmp/cache", batch_size=1).model_version
    )
    assert default.model_version != EmbeddingConfig(overlap_tokens=32).model_version
    for kwargs in ({"max_tokens": 513}, {"overlap_tokens": 510}, {"batch_size": 0}):
        with pytest.raises(ValueError):
            EmbeddingConfig(**kwargs)


def test_serving_load_is_pinned_offline_and_disallows_remote_code(monkeypatch):
    import sys
    from types import SimpleNamespace

    from src.embeddings.config import MODEL_ID, MODEL_REVISION

    loaded = []

    def load(*args, **kwargs):
        loaded.append((args, kwargs))
        return Model()

    monkeypatch.setitem(
        sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=load)
    )
    encoder = LocalEmbeddingEncoder(EmbeddingConfig(cache_directory="/synthetic/cache"))
    model = encoder._load()
    assert loaded == [
        (
            (MODEL_ID,),
            {
                "revision": MODEL_REVISION,
                "cache_folder": "/synthetic/cache",
                "device": "cpu",
                "local_files_only": True,
                "trust_remote_code": False,
            },
        )
    ]
    assert model.training is False and model.device == "cpu"
