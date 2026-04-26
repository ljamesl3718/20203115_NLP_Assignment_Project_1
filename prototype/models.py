from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


VALID_MODES = {"auto", "heuristic", "openai"}


@dataclass
class RequirementMatch:
    requirement: str
    evidence: str
    note: str
    score: float = 0.0


@dataclass
class GenerationRequest:
    resume_text: str
    activity_text: str
    job_posting_text: str
    goal: str = "internship application"
    mode: str = "auto"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GenerationRequest":
        request = cls(
            resume_text=str(payload.get("resume_text", "")),
            activity_text=str(payload.get("activity_text", "")),
            job_posting_text=str(payload.get("job_posting_text", "")),
            goal=str(payload.get("goal", "internship application")),
            mode=str(payload.get("mode", "auto")),
        )
        request.validate()
        return request

    def validate(self) -> None:
        self.resume_text = self.resume_text.strip()
        self.activity_text = self.activity_text.strip()
        self.job_posting_text = self.job_posting_text.strip()
        self.goal = self.goal.strip() or "internship application"
        self.mode = self.mode.strip().lower() or "auto"
        if not self.resume_text:
            raise ValueError("resume_text is required.")
        if not self.job_posting_text:
            raise ValueError("job_posting_text is required.")
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(VALID_MODES)}.")


@dataclass
class GenerationResponse:
    backend: str
    language: str
    model: str | None
    extracted_requirements: list[str]
    tailored_summary: str
    resume_bullets: list[str]
    cover_letter_points: list[str]
    evidence_matches: list[RequirementMatch]
    evidence_gaps: list[str]
    checklist: list[str]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_matches"] = [asdict(item) for item in self.evidence_matches]
        return payload

