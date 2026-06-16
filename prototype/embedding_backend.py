from __future__ import annotations

import os
from functools import lru_cache

import numpy as np

from .heuristics import (
    build_checklist,
    build_cover_letter_points,
    build_resume_bullets,
    build_summary,
    detect_language,
    extract_gaps,
    extract_requirements,
    gather_evidence_lines,
    score_evidence,
    truncate,
)
from .models import GenerationRequest, GenerationResponse, RequirementMatch


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def embedding_model_name() -> str:
    return os.getenv("LOCAL_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def embedding_backend_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        return False
    return True


@lru_cache(maxsize=1)
def load_embedding_model():
    from sentence_transformers import SentenceTransformer

    local_only = os.getenv("LOCAL_EMBEDDING_LOCAL_FILES_ONLY", "").lower() in {"1", "true", "yes"}
    local_only = local_only or bool(os.getenv("HF_HUB_OFFLINE"))
    return SentenceTransformer(embedding_model_name(), local_files_only=local_only)


def cosine_matrix(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left_norm = np.linalg.norm(left, axis=1, keepdims=True)
    right_norm = np.linalg.norm(right, axis=1, keepdims=True)
    left_safe = left / np.maximum(left_norm, 1e-12)
    right_safe = right / np.maximum(right_norm, 1e-12)
    return left_safe @ right_safe.T


def build_embedding_note(requirement: str, evidence: str, score: float, semantic_similarity: float) -> str:
    confidence = embedding_confidence(score, semantic_similarity, score_evidence(requirement, evidence)[1])
    if confidence == "strong":
        return f"Strong AI match. Embedding similarity: {semantic_similarity:.2f}."
    if confidence == "medium":
        return f"Moderate AI match. Embedding similarity: {semantic_similarity:.2f}; wording should be tied more directly to the job post."
    lexical_score, _, _ = score_evidence(requirement, evidence)
    if lexical_score >= 3.0:
        return "Lexical evidence exists, but the AI embedding match is weaker than ideal."
    return "Weak evidence match. This requirement may need stronger proof or a new example."


def embedding_confidence(score: float, semantic_similarity: float, keyword_coverage: float) -> str:
    if score >= 5.2 and semantic_similarity >= 0.6:
        return "strong"
    if score >= 5.2 and semantic_similarity >= 0.5 and keyword_coverage >= 0.2:
        return "strong"
    if score >= 3.8 and semantic_similarity >= 0.45:
        return "medium"
    if score >= 4.2 and keyword_coverage >= 0.2:
        return "medium"
    return "weak"


def assign_unique_evidence(pair_scores: list[list[tuple[float, int, float, float]]]) -> dict[int, tuple[float, int, float, float]]:
    assignments: dict[int, tuple[float, int, float, float]] = {}
    used_evidence: set[int] = set()
    all_pairs: list[tuple[float, int, int, float, float]] = []
    for req_index, scores in enumerate(pair_scores):
        for score, evidence_index, keyword_coverage, semantic_similarity in scores:
            all_pairs.append((score, req_index, evidence_index, keyword_coverage, semantic_similarity))
    all_pairs.sort(reverse=True, key=lambda item: item[0])

    for score, req_index, evidence_index, keyword_coverage, semantic_similarity in all_pairs:
        if req_index in assignments or evidence_index in used_evidence:
            continue
        assignments[req_index] = (score, evidence_index, keyword_coverage, semantic_similarity)
        used_evidence.add(evidence_index)

    for req_index, scores in enumerate(pair_scores):
        if req_index in assignments:
            continue
        unused = [item for item in scores if item[1] not in used_evidence]
        selected = max(unused or scores, key=lambda item: item[0])
        assignments[req_index] = selected
        used_evidence.add(selected[1])

    return assignments


def rank_matches_with_embeddings(requirements: list[str], evidence_lines: list[str]) -> list[RequirementMatch]:
    if not requirements or not evidence_lines:
        return []

    model = load_embedding_model()
    requirement_embeddings = np.asarray(model.encode(requirements, normalize_embeddings=True))
    evidence_embeddings = np.asarray(model.encode(evidence_lines, normalize_embeddings=True))
    similarities = cosine_matrix(requirement_embeddings, evidence_embeddings)

    pair_scores: list[list[tuple[float, int, float, float]]] = []
    for req_index, requirement in enumerate(requirements):
        scored: list[tuple[float, int, float, float]] = []
        for evidence_index, line in enumerate(evidence_lines):
            lexical_score, keyword_coverage, _ = score_evidence(requirement, line)
            semantic_similarity = max(0.0, float(similarities[req_index, evidence_index]))
            score = lexical_score * 0.35 + semantic_similarity * 7.5 + keyword_coverage * 1.4
            scored.append((score, evidence_index, keyword_coverage, semantic_similarity))
        pair_scores.append(scored)

    assignments = assign_unique_evidence(pair_scores)
    matches: list[RequirementMatch] = []
    for req_index, requirement in enumerate(requirements):
        score, evidence_index, keyword_coverage, semantic_similarity = assignments[req_index]
        evidence = evidence_lines[evidence_index]
        matches.append(
            RequirementMatch(
                requirement=requirement,
                evidence=truncate(evidence, 140),
                note=build_embedding_note(requirement, evidence, score, semantic_similarity),
                score=round(score, 2),
                confidence=embedding_confidence(score, semantic_similarity, keyword_coverage),
                keyword_coverage=round(keyword_coverage, 2),
            )
        )
    return matches


def generate_with_embeddings(request: GenerationRequest) -> GenerationResponse:
    language = detect_language(request.resume_text, request.activity_text, request.job_posting_text)
    requirements = extract_requirements(request.job_posting_text, limit=5)
    evidence_lines = gather_evidence_lines(request.resume_text, request.activity_text)
    matches = rank_matches_with_embeddings(requirements, evidence_lines)
    gaps = extract_gaps(requirements, matches, language)
    overall_fit_score = round(sum(match.score for match in matches) / len(matches), 2) if matches else 0.0
    coverage_rate = round(
        sum(1 for match in matches if match.confidence in {"strong", "medium"}) / max(len(requirements), 1),
        2,
    )
    response = GenerationResponse(
        backend="embedding",
        language=language,
        model=embedding_model_name(),
        extracted_requirements=requirements,
        tailored_summary=build_summary(matches, request, language),
        resume_bullets=build_resume_bullets(matches, language),
        cover_letter_points=build_cover_letter_points(matches, gaps, language),
        evidence_matches=matches,
        evidence_gaps=gaps,
        checklist=build_checklist(gaps, language),
        overall_fit_score=overall_fit_score,
        coverage_rate=coverage_rate,
        warnings=[],
    )
    if not evidence_lines:
        response.warnings.append("No evidence lines were found in the resume/activity text.")
    return response
