from __future__ import annotations

from .models import GenerationRequest


def build_application_prompt(request: GenerationRequest) -> str:
    return f"""
Return valid JSON only.

Schema:
{{
  "language": "ko or en",
  "extracted_requirements": ["string", "string", "string"],
  "tailored_summary": "string",
  "resume_bullets": ["string", "string", "string"],
  "cover_letter_points": ["string", "string", "string"],
  "evidence_matches": [
    {{
      "requirement": "string",
      "evidence": "string",
      "note": "string",
      "score": 0.0
    }}
  ],
  "evidence_gaps": ["string", "string", "string"],
  "checklist": ["string", "string", "string", "string"]
}}

Rules:
- Ground every output in the provided profile and activity text.
- Do not invent achievements, metrics, leadership roles, or technologies.
- Match the dominant language of the inputs. If most of the content is Korean, answer in Korean.
- Keep the tailored summary to 2 sentences maximum.
- Keep resume_bullets and cover_letter_points concise and immediately reusable.
- evidence_matches should explain how a real piece of evidence supports one requirement.
- If evidence is weak, say so clearly in note and surface it in evidence_gaps.

Target goal:
{request.goal}

[BASE RESUME]
{request.resume_text}

[ACTIVITY BANK]
{request.activity_text or "(none provided)"}

[JOB POSTING]
{request.job_posting_text}
""".strip()


OPENAI_INSTRUCTIONS = (
    "You are a careful internship-application tailoring assistant. "
    "You help Korean undergraduates match real experiences to a specific job posting. "
    "Output must be valid JSON only, and you must stay grounded in the provided materials."
)

