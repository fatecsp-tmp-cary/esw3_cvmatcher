"""Request-scoped staged matching over current, successfully enriched jobs."""

import hashlib
import json
import logging
import time
from collections.abc import Callable
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.embeddings.config import EmbeddingConfig
from src.embeddings.retrieval import retrieve_semantic
from src.embeddings.service import ready_predicate as embedding_ready
from src.extraction.service import ready_predicate as extraction_ready
from src.extraction.taxonomy import find_skills, normalize_skill
from src.indexing.textual import any_term_query, job_search_document
from src.matching.ranking import RankingPolicy, SimilarityCalibration
from src.matching.semantic import ExperienceScore, semantic_score
from src.matching.textual import candidate_query_text, retrieve_textual
from src.normalization.candidate.curriculum import normalize_curriculum
from src.persistence.job.job import Job, JobStatus
from src.schemas.candidate.curriculum import CurriculumRequest
from src.schemas.matches import MatchedJob, MatchesResponse, MatchResult

logger = logging.getLogger(__name__)


class QueryEncoder(Protocol):
    config: EmbeddingConfig

    @property
    def model_version(self) -> str: ...

    def encode_queries(self, texts: list[str]) -> list[list[float]]: ...


class MatchingPipeline:
    def __init__(
        self,
        sessions: Callable[[], Session],
        encoder: QueryEncoder,
        extraction_version: str,
        *,
        ranking: RankingPolicy | None = None,
        calibration: SimilarityCalibration | None = None,
    ):
        self.sessions = sessions
        self.encoder = encoder
        self.extraction_version = extraction_version
        self.ranking = ranking or RankingPolicy()
        self.calibration = calibration or SimilarityCalibration()

    @property
    def algorithm_version(self) -> str:
        config = {
            "textual": self.ranking.textual,
            "semantic": self.ranking.semantic,
            "structured": self.ranking.structured,
            "pool": self.ranking.retrieval_limit,
            "zero": self.calibration.zero,
            "full": self.calibration.full,
            "extraction": self.extraction_version,
            "semantic_policy": "semantic-aggregation-v1-provisional",
        }
        digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]
        return f"{self.ranking.version}:{self.calibration.version}:{digest}"

    def __call__(self, request: CurriculumRequest, limit: int) -> MatchesResponse:
        started = time.perf_counter()
        try:
            return self._match(request, limit)
        finally:
            # No submitted identity, candidate content, embeddings or result fields.
            logger.info("matching_duration_ms=%.3f", (time.perf_counter() - started) * 1000)

    def _match(self, request: CurriculumRequest, limit: int) -> MatchesResponse:
        import numpy as np

        candidate = normalize_curriculum(request)
        query_text = candidate_query_text(candidate)
        if not query_text.strip():
            return MatchesResponse(matches=[])
        # Each entry is embedded separately, once per request. No candidate cache.
        experience_texts = [f"{x.title}\n{x.description}" for x in candidate.experience]
        education_texts = [f"{x.course}\n{x.level}" for x in candidate.education]
        texts = experience_texts + education_texts
        vectors = self.encoder.encode_queries(texts or [query_text])
        if len(vectors) != len(texts or [query_text]):
            raise ValueError("Invalid embedding result count")
        from src.embeddings.encoder import normalized_vector

        vectors = [normalized_vector(vector) for vector in vectors]
        config = self.encoder.config
        gate = extraction_ready(self.extraction_version)
        with self.sessions() as session:
            pool: set[int] = set()
            for job, _ in retrieve_textual(
                session, candidate, readiness=gate, limit=self.ranking.retrieval_limit
            ):
                pool.add(job.id)
            for vector in vectors:
                for job, _ in retrieve_semantic(
                    session,
                    vector,
                    config,
                    self.extraction_version,
                    limit=self.ranking.retrieval_limit,
                ):
                    pool.add(job.id)
            if not pool:
                return MatchesResponse(matches=[])
            jobs = session.scalars(
                select(Job)
                .where(Job.id.in_(sorted(pool)), Job.status == JobStatus.ACTIVE, gate)
                .order_by(Job.platform, Job.source_job_id, Job.id)
                .execution_options(populate_existing=True)
            ).all()
            # Recheck all readiness after pool retrieval; no stale embeddings are scored.
            vector_jobs = set(
                session.scalars(
                    select(Job.id).where(
                        Job.id.in_(sorted(pool)),
                        embedding_ready(config, self.extraction_version),
                    )
                )
            )
            document = job_search_document()
            query = any_term_query(query_text)
            text_scores: dict[int, float] = dict(
                session.execute(
                    select(Job.id, func.ts_rank_cd(document, query, 32) * 100.0).where(
                        Job.id.in_(sorted(pool))
                    )
                ).all()
            )
            scored = []
            entry_matrix: Any = np.asarray(vectors[: len(texts)], dtype=np.float64)
            for job in jobs:
                semantic = 0.0
                if texts and job.id in vector_jobs and job.embedding is not None:
                    job_vector: Any = np.asarray(normalized_vector(job.embedding), dtype=np.float64)
                    similarities = np.clip(entry_matrix @ job_vector, -1.0, 1.0)
                    entry_scores = [self.calibration.score(float(value)) for value in similarities]
                    experiences = tuple(
                        ExperienceScore(entry_scores[i], entry.start_date, entry.end_date)
                        for i, entry in enumerate(candidate.experience)
                    )
                    semantic = semantic_score(
                        experiences, tuple(entry_scores[len(experience_texts) :])
                    )
                skills = {normalize_skill(skill) for skill in (job.skills or []) if skill.strip()}
                matched = find_skills([query_text], skills)
                structured = 100.0 * len(matched & skills) / len(skills) if skills else 0.0
                total = self.ranking.score(float(text_scores.get(job.id, 0)), semantic, structured)
                scored.append((total, job, sorted(matched & skills)))
            scored.sort(
                key=lambda item: (
                    -item[0],
                    item[1].platform,
                    item[1].source_job_id,
                    item[1].id,
                )
            )
            matches = []
            for rank, (score, job, matched_skills) in enumerate(scored[:limit], start=1):
                payload = {name: getattr(job, name) for name in MatchedJob.model_fields}
                matches.append(
                    MatchResult(
                        rank=rank,
                        job=MatchedJob(**payload),
                        score=score,
                        eligibility=True,
                        matched_skills=matched_skills,
                        # Mandatory model classifications stay disabled pending measured quality.
                        missing_requirements=[],
                        embedding_model=self.encoder.model_version,
                        algorithm_version=self.algorithm_version,
                    )
                )
            return MatchesResponse(matches=matches)
