from __future__ import annotations

import math
import re
from collections import Counter

from .models import GenerationRequest, GenerationResponse, RequirementMatch


EN_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
    "will",
    "you",
    "your",
    "our",
    "this",
    "we",
    "who",
    "have",
    "has",
    "had",
    "their",
    "they",
    "them",
    "role",
    "team",
    "job",
    "position",
    "intern",
    "internship",
    "preferred",
    "required",
    "requirements",
    "qualification",
    "qualifications",
    "experience",
    "experiences",
    "skill",
    "skills",
}

KO_STOPWORDS = {
    "그리고",
    "관련",
    "대한",
    "또는",
    "위한",
    "에서",
    "하는",
    "있는",
    "업무",
    "역량",
    "경험",
    "우대",
    "필수",
    "지원",
    "채용",
    "이상",
    "기반",
    "통해",
    "대한",
    "등의",
    "및",
    "수행",
    "가능한",
    "분",
    "자",
    "합니다",
    "입니다",
}

ACTION_HINTS = {
    "built",
    "created",
    "led",
    "launched",
    "organized",
    "designed",
    "implemented",
    "improved",
    "analyzed",
    "managed",
    "developed",
    "conducted",
    "운영",
    "기획",
    "분석",
    "개발",
    "제작",
    "수행",
    "개선",
    "주도",
}

LINE_HINTS = (
    "responsibilities",
    "requirements",
    "preferred",
    "qualifications",
    "what you will do",
    "what we're looking for",
    "you will",
    "should",
    "must",
    "자격",
    "우대",
    "필수",
    "주요",
    "역할",
    "업무",
    "담당",
)


def detect_language(*texts: str) -> str:
    joined = "\n".join(texts)
    hangul_count = len(re.findall(r"[가-힣]", joined))
    latin_count = len(re.findall(r"[A-Za-z]", joined))
    return "ko" if hangul_count > latin_count else "en"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9+#./-]*|[0-9]+(?:\.[0-9]+)?|[가-힣]{2,}", text.lower())


def keyword_tokens(text: str) -> list[str]:
    lang = detect_language(text)
    stopwords = KO_STOPWORDS if lang == "ko" else EN_STOPWORDS
    return [token for token in tokenize(text) if token not in stopwords and len(token) > 1]


def split_lines(text: str) -> list[str]:
    chunks = re.split(r"[\r\n]+|(?<=[.!?])\s+", text)
    results: list[str] = []
    for chunk in chunks:
        line = re.sub(r"\s+", " ", chunk).strip(" -•\t")
        if 12 <= len(line) <= 260:
            results.append(line)
    return results


def compact_phrase(text: str, limit: int = 72) -> str:
    text = re.sub(r"^\d+[\).]\s*", "", text).strip(" -•\t")
    if len(text) <= limit:
        return text
    first_clause = re.split(r"[;,:()]", text)[0].strip()
    if 8 <= len(first_clause) <= limit:
        return first_clause
    return text[: limit - 3].rstrip() + "..."


def extract_requirements(job_posting_text: str, limit: int = 5) -> list[str]:
    raw_lines = [line.strip() for line in re.split(r"[\r\n]+", job_posting_text) if line.strip()]
    candidates: list[str] = []
    heading_like = {
        "responsibilities",
        "qualifications",
        "requirements",
        "preferred",
        "business / product operations intern",
        "job description",
        "담당 업무",
        "자격 요건",
        "우대 사항",
    }
    for line in raw_lines:
        stripped = line.strip()
        lower = stripped.lower().strip(" -•\t")
        tokens = keyword_tokens(stripped)
        if lower in heading_like:
            continue
        if len(tokens) < 3:
            continue
        if stripped.startswith(("-", "•")) or any(hint in lower for hint in LINE_HINTS):
            candidates.append(compact_phrase(stripped))
    deduped: list[str] = []
    seen = set()
    for candidate in candidates:
        key = " ".join(keyword_tokens(candidate)[:5]) or candidate.lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(candidate)
        if len(deduped) >= limit:
            return deduped

    sentence_fallback = [compact_phrase(line) for line in split_lines(job_posting_text) if len(keyword_tokens(line)) >= 3]
    for phrase in sentence_fallback:
        if phrase.lower() not in seen:
            deduped.append(phrase)
            seen.add(phrase.lower())
        if len(deduped) >= limit:
            break
    if len(deduped) < limit:
        counts = Counter(keyword_tokens(job_posting_text))
        fallback = [token for token, _ in counts.most_common(limit * 2)]
        for token in fallback:
            phrase = token.title() if detect_language(token) == "en" else token
            if phrase.lower() not in seen:
                deduped.append(phrase)
                seen.add(phrase.lower())
            if len(deduped) >= limit:
                break
    return deduped[:limit] or ["Tailored communication", "Relevant project experience", "Role-specific motivation"]


def gather_evidence_lines(resume_text: str, activity_text: str) -> list[str]:
    lines = split_lines(f"{resume_text}\n{activity_text}")
    if lines:
        return lines
    combined = re.sub(r"\s+", " ", f"{resume_text} {activity_text}").strip()
    return [combined] if combined else []


def score_evidence(requirement: str, evidence_line: str) -> float:
    req_tokens = set(keyword_tokens(requirement))
    evidence_tokens = set(keyword_tokens(evidence_line))
    overlap = len(req_tokens & evidence_tokens)
    score = overlap * 4.0
    if re.search(r"\d", evidence_line):
        score += 1.5
    if any(token in evidence_line.lower() for token in ACTION_HINTS):
        score += 1.0
    score += min(len(evidence_tokens) / 50.0, 1.5)
    return score


def truncate(text: str, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def rank_matches(requirements: list[str], evidence_lines: list[str]) -> list[RequirementMatch]:
    matches: list[RequirementMatch] = []
    used_lines: set[int] = set()
    for requirement in requirements:
        scored = []
        for index, line in enumerate(evidence_lines):
            base_score = score_evidence(requirement, line)
            penalty = 0.8 if index in used_lines else 0.0
            scored.append((base_score - penalty, index, line))
        scored.sort(reverse=True, key=lambda item: item[0])
        if scored:
            best_score, best_index, best_line = scored[0]
            used_lines.add(best_index)
            matches.append(
                RequirementMatch(
                    requirement=requirement,
                    evidence=truncate(best_line, 140),
                    note=build_note(requirement, best_line, best_score),
                    score=round(best_score, 2),
                )
            )
    return matches


def build_note(requirement: str, evidence: str, score: float) -> str:
    req_tokens = set(keyword_tokens(requirement))
    evidence_tokens = set(keyword_tokens(evidence))
    overlap = sorted(req_tokens & evidence_tokens)
    if overlap:
        overlap_preview = ", ".join(overlap[:3])
        return f"Shared signal: {overlap_preview}."
    if score >= 2.5:
        return "Relevant experience exists, but the wording should be tied to the job post more clearly."
    return "Weak evidence match. This requirement may need stronger proof or a new example."


def extract_gaps(requirements: list[str], matches: list[RequirementMatch], language: str) -> list[str]:
    gaps = [match.requirement for match in matches if match.score < 2.5]
    missing = requirements[len(gaps) :]
    selected = (gaps + missing)[:3]
    if selected:
        return selected
    if language == "ko":
        return ["정량 성과를 더 명확히 제시하기", "공고 용어와 경험 서술 연결하기", "지원 동기 근거 보강하기"]
    return [
        "Add quantified outcomes where possible",
        "Mirror the job-post language more directly",
        "Strengthen evidence for motivation and fit",
    ]


def build_summary(matches: list[RequirementMatch], request: GenerationRequest, language: str) -> str:
    top_requirements = [compact_phrase(match.requirement, 36) for match in matches[:3]]
    top_evidence = truncate(matches[0].evidence, 80) if matches else truncate(request.resume_text, 80)
    if language == "ko":
        joined = ", ".join(top_requirements) if top_requirements else "핵심 요구 역량"
        return (
            f"{request.goal}에 맞춰 {joined} 역량을 전면에 보이도록 지원 스토리를 재구성했습니다. "
            f"특히 '{top_evidence}' 경험을 중심 증거로 두는 구성이 적합합니다."
        )
    joined = ", ".join(top_requirements) if top_requirements else "the role's key requirements"
    return (
        f"This application package emphasizes {joined} for the {request.goal}. "
        f"The strongest proof point to foreground is '{top_evidence}'."
    )


def build_resume_bullets(matches: list[RequirementMatch], language: str) -> list[str]:
    bullets = []
    for match in matches[:3]:
        requirement = compact_phrase(match.requirement, 34)
        evidence = truncate(match.evidence, 96)
        if language == "ko":
            bullets.append(f"{evidence} 경험을 바탕으로 {requirement} 역량을 직무 맥락에 맞게 강조합니다.")
        else:
            bullets.append(f"Highlight {requirement} by anchoring it in this evidence: {evidence}.")
    if len(bullets) < 3:
        filler = "Add one quantified achievement that directly supports the target role."
        while len(bullets) < 3:
            bullets.append(filler if language == "en" else "지원 직무와 직접 연결되는 정량 성과 한 줄을 추가합니다.")
    return bullets


def build_cover_letter_points(matches: list[RequirementMatch], gaps: list[str], language: str) -> list[str]:
    points = []
    for match in matches[:2]:
        requirement = compact_phrase(match.requirement, 34)
        evidence = truncate(match.evidence, 86)
        if language == "ko":
            points.append(f"{requirement}이 왜 중요한지 먼저 짚고, {evidence} 경험으로 연결해 설득합니다.")
        else:
            points.append(f"Explain why {requirement} matters for the role, then connect it to {evidence}.")
    if gaps:
        gap = compact_phrase(gaps[0], 34)
        if language == "ko":
            points.append(f"{gap} 부분은 현재 근거가 약하므로, 학습 의지나 빠른 적응 사례로 보완합니다.")
        else:
            points.append(f"Acknowledge the weaker area around {gap}, then address it with a fast-learning or adaptability example.")
    return points[:3]


def build_checklist(gaps: list[str], language: str) -> list[str]:
    if language == "ko":
        items = [
            "공고의 핵심 표현을 이력서 상단 요약과 bullet에 반영하기",
            "가능한 항목에는 수치, 기간, 산출물을 넣어 성과를 구체화하기",
            f"근거가 약한 항목: {compact_phrase(gaps[0], 24) if gaps else '지원 동기'} 보완하기",
            "최종 문장이 과장되지 않고 본인 경험에 기반하는지 점검하기",
        ]
    else:
        items = [
            "Mirror the highest-priority phrases from the job post in the summary and top bullets",
            "Quantify outcomes with numbers, scope, or deliverables wherever possible",
            f"Strengthen the weakest evidence area: {compact_phrase(gaps[0], 24) if gaps else 'motivation'}",
            "Do a final authenticity check so the application still sounds grounded in real work",
        ]
    return items


def generate_with_heuristics(request: GenerationRequest) -> GenerationResponse:
    language = detect_language(request.resume_text, request.activity_text, request.job_posting_text)
    requirements = extract_requirements(request.job_posting_text, limit=5)
    evidence_lines = gather_evidence_lines(request.resume_text, request.activity_text)
    matches = rank_matches(requirements, evidence_lines)
    gaps = extract_gaps(requirements, matches, language)
    response = GenerationResponse(
        backend="heuristic",
        language=language,
        model=None,
        extracted_requirements=requirements,
        tailored_summary=build_summary(matches, request, language),
        resume_bullets=build_resume_bullets(matches, language),
        cover_letter_points=build_cover_letter_points(matches, gaps, language),
        evidence_matches=matches[:4],
        evidence_gaps=gaps,
        checklist=build_checklist(gaps, language),
        warnings=[],
    )
    if not evidence_lines:
        response.warnings.append("No evidence lines were found in the resume/activity text.")
    return response
