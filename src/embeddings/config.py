"""Pinned local CPU embedding identity and deterministic windowing policy."""

import hashlib
import json
from dataclasses import dataclass

MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
DIMENSIONS = 384
JOB_TEXT_VERSION = "title-skills-requirements-description-sorted-location-mode-v2"


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    cache_directory: str | None = None
    max_tokens: int = 512
    overlap_tokens: int = 64
    batch_size: int = 8

    def __post_init__(self) -> None:
        if (
            type(self.max_tokens) is not int
            or not 8 <= self.max_tokens <= 512
            or type(self.overlap_tokens) is not int
            or not 0 <= self.overlap_tokens < self.max_tokens - 4
            or type(self.batch_size) is not int
            or not 1 <= self.batch_size <= 32
        ):
            raise ValueError("Invalid bounded embedding window/batch policy")

    @property
    def policy_version(self) -> str:
        policy = {
            "algorithm": "e5-full-token-windows-weighted-mean-v1",
            "max_tokens": self.max_tokens,
            "overlap_tokens": self.overlap_tokens,
            "dimensions": DIMENSIONS,
            "query_prefix": "query: ",
            "passage_prefix": "passage: ",
            "normalization": "l2-each-window-and-aggregate",
            "job_text": JOB_TEXT_VERSION,
        }
        encoded = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @property
    def model_version(self) -> str:
        return f"{MODEL_ID}@{MODEL_REVISION}:{self.policy_version}"
