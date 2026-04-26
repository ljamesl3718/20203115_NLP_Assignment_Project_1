from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from prototype.models import GenerationRequest
from prototype.service import generate_application_package


ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "static"
SAMPLE_DIR = ROOT_DIR / "sample_data"


def load_sample_payload() -> dict[str, str]:
    return {
        "resume_text": (SAMPLE_DIR / "student_profile.txt").read_text(encoding="utf-8"),
        "activity_text": (SAMPLE_DIR / "activity_bank.txt").read_text(encoding="utf-8"),
        "job_posting_text": (SAMPLE_DIR / "job_posting.txt").read_text(encoding="utf-8"),
        "goal": "internship application for a product or business role",
    }


class PrototypeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "openai_key_present": bool(os.getenv("OPENAI_API_KEY")),
                    "sample_ready": SAMPLE_DIR.exists(),
                }
            )
            return

        if self.path == "/api/sample":
            self._send_json(load_sample_payload())
            return

        if self.path in {"/", "/index.html"}:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/generate":
            self._send_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(raw_body or "{}")
            request = GenerationRequest.from_dict(payload)
            response = generate_application_package(request)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": f"Generation failed: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json(response.to_dict())


def main() -> None:
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), PrototypeHandler)
    print(f"Tailored Application Coach running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

