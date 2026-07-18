from __future__ import annotations

import argparse
import json
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from auto_clip.cli import run_pipeline
from auto_clip.config import RunRequest


class ProcessorHandler(BaseHTTPRequestHandler):
    server_version = "AutoClipProcessor/0.1"

    def _json_response(self, payload: dict[str, object], status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json_response(
                {
                    "ok": True,
                    "service": "auto-clip-processor",
                    "work_dir": str(self.server.work_dir),
                }
            )
            return

        self._json_response({"ok": False, "error": "Not Found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/process":
            self._json_response({"ok": False, "error": "Not Found"}, status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            self._json_response({"ok": False, "error": "Empty payload"}, status=400)
            return

        raw = self.rfile.read(content_length)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json_response({"ok": False, "error": "Invalid JSON"}, status=400)
            return

        source = payload.get("source") if isinstance(payload, dict) else None
        if not isinstance(source, str) or not source.strip():
            self._json_response({"ok": False, "error": "Field 'source' is required"}, status=400)
            return

        job_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(job_id, str) or not job_id:
            job_id = "manual"

        config_path = None
        config_data = payload.get("config") if isinstance(payload, dict) else None
        if config_data is not None:
            if not isinstance(config_data, dict):
                self._json_response({"ok": False, "error": "Field 'config' must be an object"}, status=400)
                return

            config_dir = self.server.work_dir / "webhook_configs"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / f"{job_id}.json"
            config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
            config_path = str(config_file)

        request = RunRequest(source=source, config_path=config_path, work_dir=str(self.server.work_dir))

        try:
            summary = run_pipeline(request)
            self._json_response(
                {
                    "ok": True,
                    "processed": True,
                    "job_id": job_id,
                    "source_id": summary.get("source_id"),
                    "candidate_count": summary.get("candidate_count"),
                    "clip_count": len(summary.get("clips", [])),
                    "summary": summary,
                },
                status=HTTPStatus.ACCEPTED,
            )
        except Exception as exc:  # pragma: no cover
            self._json_response(
                {
                    "ok": False,
                    "processed": False,
                    "error": str(exc),
                    "trace": traceback.format_exc(),
                },
                status=500,
            )


class ProcessorServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], work_dir: Path) -> None:
        super().__init__(server_address, ProcessorHandler)
        self.work_dir = work_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto Clip Processor Webhook")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--work-dir", default="artifacts")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    server = ProcessorServer((args.host, args.port), work_dir=work_dir)
    print(f"Processor webhook listening on http://{args.host}:{args.port}")
    print("POST /process to execute jobs, GET /health for readiness")
    server.serve_forever()


if __name__ == "__main__":
    main()
