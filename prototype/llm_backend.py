from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .models import GenerationRequest, GenerationResponse, RequirementMatch
from .prompts import OPENAI_INSTRUCTIONS, build_application_prompt


API_URL = "https://api.openai.com/v1/responses"


def openai_api_key_present() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def collect_output_text(payload: dict[str, Any]) -> str:
    pieces: list[str] = []
    top_level = payload.get("output_text")
    if isinstance(top_level, str) and top_level.strip():
        pieces.append(top_level.strip())

    # Responses can contain multiple output items, so aggregate every output_text block.
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                pieces.append(str(content["text"]).strip())
    return "\n".join(piece for piece in pieces if piece).strip()


def extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    if start < 0:
        raise ValueError("Model output did not contain a JSON object.")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : index + 1])
    raise ValueError("Could not find a complete JSON object in the model output.")


def normalize_text_list(value: Any, fallback: list[str], limit: int) -> list[str]:
    if not isinstance(value, list):
        return fallback[:limit]
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:limit] or fallback[:limit]


def normalize_matches(value: Any) -> list[RequirementMatch]:
    if not isinstance(value, list):
        return []
    matches: list[RequirementMatch] = []
    for item in value[:4]:
        if not isinstance(item, dict):
            continue
        matches.append(
            RequirementMatch(
                requirement=str(item.get("requirement", "")).strip(),
                evidence=str(item.get("evidence", "")).strip(),
                note=str(item.get("note", "")).strip(),
                score=float(item.get("score", 0.0) or 0.0),
            )
        )
    return [match for match in matches if match.requirement and match.evidence]


def call_openai(request: GenerationRequest) -> GenerationResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")

    model = os.getenv("OPENAI_MODEL", "gpt-5.4")
    body: dict[str, Any] = {
        "model": model,
        "instructions": OPENAI_INSTRUCTIONS,
        "input": build_application_prompt(request),
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    if os.getenv("OPENAI_ORGANIZATION"):
        headers["OpenAI-Organization"] = os.getenv("OPENAI_ORGANIZATION", "")
    if os.getenv("OPENAI_PROJECT"):
        headers["OpenAI-Project"] = os.getenv("OPENAI_PROJECT", "")

    http_request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(http_request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API request failed with HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"OpenAI API request failed: {error.reason}") from error

    output_text = collect_output_text(payload)
    structured = extract_json_object(output_text)

    return GenerationResponse(
        backend="openai",
        language=str(structured.get("language", "en")).strip() or "en",
        model=model,
        extracted_requirements=normalize_text_list(structured.get("extracted_requirements"), [], 5),
        tailored_summary=str(structured.get("tailored_summary", "")).strip(),
        resume_bullets=normalize_text_list(structured.get("resume_bullets"), [], 3),
        cover_letter_points=normalize_text_list(structured.get("cover_letter_points"), [], 3),
        evidence_matches=normalize_matches(structured.get("evidence_matches")),
        evidence_gaps=normalize_text_list(structured.get("evidence_gaps"), [], 3),
        checklist=normalize_text_list(structured.get("checklist"), [], 4),
        warnings=[],
    )

