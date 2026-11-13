"""Request-scoped staged matching over current, successfully enriched jobs."""

import hashlib
import json
import logging
import time
from collections.abc import Callable
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.requirements import VERSION as REQUIREMENTS_VERSION
from src.domain.requirements import comparable_score
from src.embeddings.config import EmbeddingConfig
from src.embeddings.retrieval import retrieve_semantic
from src.embeddings.service import ready_predicate as embedding_ready
from src.extraction.service import ready_predicate as extraction_ready
from src.extraction.taxonomy import _ALIASES, find_skills, normalize_skill
from src.indexing.textual import TEXTUAL_VERSION
from src.matching.ranking import RankingPolicy, SimilarityCalibration
from src.matching.semantic import ExperienceScore, selected_experience_indices, semantic_score
from src.matching.textual import candidate_query_text, retrieve_textual, textual_statement
from src.normalization.candidate.curriculum import normalize_curriculum
from src.persistence.job.job import ACTIVE_STATUSES, INACTIVE_STATUSES, Job, status_predicate
from src.persistence.job.skill import JobRequirement, JobSkill, Skill
from src.processing import ProcessingUnavailable, checkpoint
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
            "textual_policy": TEXTUAL_VERSION,
            "structured_policy": REQUIREMENTS_VERSION,
            "semantic_policy": "semantic-aggregation-v1-provisional",
        }
        digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:16]
        return f"{self.ranking.version}:{self.calibration.version}:{digest}"

    def __call__(self, request: CurriculumRequest, limit: int) -> MatchesResponse:
        started = time.perf_counter()
        outcome = "unavailable"
        try:
            checkpoint()
            result = self._match(request, limit)
            checkpoint()
            outcome = "success" if result.matches else "empty"
            return result
        except ProcessingUnavailable:
            outcome = "budget_exhausted"
            raise
        finally:
            # Fixed outcomes only: no submitted identity, content or result fields.
            logger.info(
                "matching_duration_ms=%.3f matching_outcome=%s",
                (time.perf_counter() - started) * 1000,
                outcome,
            )

    def _match(self, request: CurriculumRequest, limit: int) -> MatchesResponse:
        import numpy as np

        checkpoint()
        candidate = normalize_curriculum(request)
        query_text = candidate_query_text(candidate)
        candidate_skills = {normalize_skill(x.description) for x in candidate.competencies}
        candidate_skills |= find_skills([query_text], _ALIASES.values())
        if not query_text.strip():
            return MatchesResponse(matches=[])
        # Each entry is embedded separately, once per request. No candidate cache.
        experience_texts = [f"{x.title}\n{x.description}" for x in candidate.experience]
        education_texts = [f"{x.course}\n{x.level}" for x in candidate.education]
        texts = experience_texts + education_texts
        checkpoint()
        vectors = self.encoder.encode_queries(texts or [query_text])
        checkpoint()
        if len(vectors) != len(texts or [query_text]):
            raise ValueError("Invalid embedding result count")
        from src.embeddings.encoder import normalized_vector

        vectors = [normalized_vector(vector) for vector in vectors]
        config = self.encoder.config
        gate = extraction_ready(self.extraction_version)
        checkpoint()
        with self.sessions() as session:
            matches: list[MatchResult] = []
            # Active jobs are ranked first; inactive jobs only complete the list (ADR-016).
            for statuses, eligible in ((ACTIVE_STATUSES, True), (INACTIVE_STATUSES, False)):
                if len(matches) >= limit:
                    break
                pool: set[int] = set()
                for job, _ in retrieve_textual(
                    session,
                    candidate,
                    readiness=gate,
                    limit=self.ranking.retrieval_limit,
                    statuses=statuses,
                ):
                    pool.add(job.id)
                checkpoint()
                for vector in vectors:
                    checkpoint()
                    for job, _ in retrieve_semantic(
                        session,
                        vector,
                        config,
                        self.extraction_version,
                        limit=self.ranking.retrieval_limit,
                        statuses=statuses,
                    ):
                        pool.add(job.id)
                if not pool:
                    continue
                checkpoint()
                jobs = session.scalars(
                    select(Job)
                    .where(Job.id.in_(sorted(pool)), status_predicate(statuses), gate)
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
                # Recompute the complete textual component (including requirement
                # rows) for the considered union, even for semantic-only retrieval.
                text_scores: dict[int, float] = {
                    job.id: float(score)
                    for job, score in session.execute(
                        textual_statement(
                            query_text, readiness=gate, limit=len(pool), statuses=statuses
                        ).where(Job.id.in_(sorted(pool)))
                    )
                }
                associated_skills: dict[int, set[str]] = {}
                for identifier, name in session.execute(
                    select(JobSkill.job_id, Skill.canonical_name)
                    .join(Skill, Skill.id == JobSkill.skill_id)
                    .where(JobSkill.job_id.in_(pool))
                ):
                    associated_skills.setdefault(identifier, set()).add(normalize_skill(name))
                requirements: dict[int, list[str]] = {}
                for identifier, text in session.execute(
                    select(JobRequirement.job_id, JobRequirement.text).where(
                        JobRequirement.job_id.in_(pool)
                    )
                ):
                    requirements.setdefault(identifier, []).append(text)
                scored = []
                entry_matrix: Any = np.asarray(vectors[: len(texts)], dtype=np.float64)
                for job in jobs:
                    checkpoint()
                    semantic = 0.0
                    relevant_experience: tuple[Any, ...] = ()
                    if texts and job.id in vector_jobs and job.embedding is not None:
                        job_vector: Any = np.asarray(
                            normalized_vector(job.embedding), dtype=np.float64
                        )
                        similarities = np.clip(entry_matrix @ job_vector, -1.0, 1.0)
                        entry_scores = [
                            self.calibration.score(float(value)) for value in similarities
                        ]
                        experiences = tuple(
                            ExperienceScore(entry_scores[i], entry.start_date, entry.end_date)
                            for i, entry in enumerate(candidate.experience)
                        )
                        semantic = semantic_score(
                            experiences, tuple(entry_scores[len(experience_texts) :])
                        )
                        relevant_experience = tuple(
                            candidate.experience[index]
                            for index in selected_experience_indices(experiences)
                            if experiences[index].score >= 50.0
                        )
                    skills = {
                        normalize_skill(skill) for skill in (job.skills or []) if skill.strip()
                    }
                    skills |= associated_skills.get(job.id, set())
                    matched = find_skills([query_text], skills)
                    structured = comparable_score(
                        candidate,
                        job,
                        skills=skills,
                        matched=matched,
                        requirements=requirements.get(job.id, []),
                        relevant_experience=relevant_experience,
                        candidate_skills=candidate_skills | matched,
                    )
                    total = self.ranking.score(
                        float(text_scores.get(job.id, 0)), semantic, structured
                    )
                    scored.append((total, job, sorted(matched & skills)))
                scored.sort(
                    key=lambda item: (
                        -item[0],
                        item[1].platform,
                        item[1].source_job_id,
                        item[1].id,
                    )
                )
                for score, job, matched_skills in scored[: limit - len(matches)]:
                    payload = {name: getattr(job, name) for name in MatchedJob.model_fields}
                    matches.append(
                        MatchResult(
                            rank=len(matches) + 1,
                            job=MatchedJob(**payload),
                            score=score,
                            eligibility=eligible,
                            matched_skills=matched_skills,
                            # Mandatory classifications stay disabled pending measured quality.
                            missing_requirements=[],
                            embedding_model=self.encoder.model_version,
                            algorithm_version=self.algorithm_version,
                        )
                    )
            return MatchesResponse(matches=matches)
