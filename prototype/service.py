from __future__ import annotations

from .embedding_backend import embedding_backend_available, generate_with_embeddings
from .heuristics import generate_with_heuristics
from .llm_backend import call_openai, openai_api_key_present
from .models import GenerationRequest, GenerationResponse


def generate_application_package(request: GenerationRequest) -> GenerationResponse:
    if request.mode == "embedding":
        return generate_with_embeddings(request)

    if request.mode == "heuristic":
        return generate_with_heuristics(request)

    if request.mode == "openai":
        response = call_openai(request)
        if not response.extracted_requirements:
            response.extracted_requirements = generate_with_heuristics(request).extracted_requirements
        return response

    if embedding_backend_available():
        try:
            return generate_with_embeddings(request)
        except Exception as exc:
            fallback = generate_with_heuristics(request)
            fallback.warnings.append(f"Local embedding model failed, so the app fell back to heuristic mode: {exc}")
            return fallback

    if openai_api_key_present():
        try:
            response = call_openai(request)
            if not response.extracted_requirements:
                response.extracted_requirements = generate_with_heuristics(request).extracted_requirements
            return response
        except Exception as exc:
            fallback = generate_with_heuristics(request)
            fallback.warnings.append(f"OpenAI mode failed, so the app fell back to heuristic mode: {exc}")
            return fallback

    fallback = generate_with_heuristics(request)
    fallback.warnings.append("OPENAI_API_KEY was not found, so the app used heuristic mode.")
    return fallback
