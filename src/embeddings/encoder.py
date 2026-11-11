"""Offline CPU inference over complete token windows, with no candidate cache."""

import math
from collections.abc import Sequence
from threading import Lock
from typing import Any

from src.embeddings.config import DIMENSIONS, MODEL_ID, MODEL_REVISION, EmbeddingConfig


def normalized_vector(values: Sequence[float]) -> list[float]:
    if len(values) != DIMENSIONS:
        raise ValueError("Invalid embedding dimensions")
    result = [float(x) for x in values]
    if any(not math.isfinite(x) for x in result):
        raise ValueError("Embedding must contain finite values")
    scale = max(abs(x) for x in result)
    if not scale:
        raise ValueError("Embedding must have nonzero norm")
    scaled = [x / scale for x in result]
    norm = math.sqrt(math.fsum(x * x for x in scaled))
    return [x / norm for x in scaled]


class LocalEmbeddingEncoder:
    """One pinned, lazily loaded CPU model; batches and calls are serialized.

    Injected models use the SentenceTransformer tokenizer/forward boundary for
    deterministic offline tests. Serving never downloads missing artifacts.
    """

    def __init__(self, config: EmbeddingConfig | None = None, *, model: Any = None):
        self.config = config or EmbeddingConfig()
        self._model = model
        self._lock = Lock()

    @property
    def model_version(self) -> str:
        return self.config.model_version

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                MODEL_ID,
                revision=MODEL_REVISION,
                cache_folder=self.config.cache_directory,
                device="cpu",
                local_files_only=True,
                trust_remote_code=False,
            )
        self._model.to("cpu")
        self._model.eval()
        return self._model

    def encode_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(texts, "query: ")

    def encode_jobs(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(texts, "passage: ")

    def _encode(self, texts: Sequence[str], prefix: str) -> list[list[float]]:
        if isinstance(texts, (str, bytes)) or any(
            not isinstance(text, str) or not text.strip() for text in texts
        ):
            raise ValueError("Embedding input must contain nonempty text entries")
        if not texts:
            return []
        import torch

        with self._lock:
            model = self._load()
            tokenizer = model.tokenizer
            prefix_ids = tokenizer(
                prefix, add_special_tokens=False, truncation=False, verbose=False
            )["input_ids"]
            capacity = (
                min(self.config.max_tokens, model.max_seq_length)
                - tokenizer.num_special_tokens_to_add(pair=False)
                - len(prefix_ids)
            )
            if capacity <= self.config.overlap_tokens:
                raise ValueError("Model window is incompatible with configured overlap")
            outputs = []
            # Work one entry at a time; no persistent query representation/cache.
            for text in texts:
                token_ids = tokenizer(
                    text, add_special_tokens=False, truncation=False, verbose=False
                )["input_ids"]
                if not token_ids:
                    raise ValueError("Embedding input must contain token evidence")
                total = [0.0] * DIMENSIONS
                features = []
                weights = []
                start = 0
                while start < len(token_ids):
                    end = min(start + capacity, len(token_ids))
                    feature = tokenizer.prepare_for_model(
                        prefix_ids + token_ids[start:end],
                        add_special_tokens=True,
                        truncation=False,
                        return_attention_mask=True,
                    )
                    if len(feature["input_ids"]) > self.config.max_tokens:
                        raise ValueError("Embedding token window exceeds configured bound")
                    features.append(feature)
                    weights.append(
                        end - start if start == 0 else end - start - self.config.overlap_tokens
                    )
                    final = end == len(token_ids)
                    if len(features) == self.config.batch_size or final:
                        batch = tokenizer.pad(features, padding=True, return_tensors="pt")
                        batch = {key: value.to("cpu") for key, value in batch.items()}
                        with torch.inference_mode():
                            encoded = model(batch)["sentence_embedding"].detach().cpu().tolist()
                        if len(encoded) != len(features):
                            raise ValueError("Embedding model returned an invalid batch")
                        for vector, weight in zip(encoded, weights, strict=True):
                            normalized = normalized_vector(vector)
                            for index, value in enumerate(normalized):
                                total[index] += value * weight
                        features.clear()
                        weights.clear()
                    if final:
                        break
                    start = end - self.config.overlap_tokens
                outputs.append(normalized_vector(total))
            return outputs
