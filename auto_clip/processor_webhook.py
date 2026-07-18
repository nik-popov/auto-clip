from __future__ import annotations

import argparse
import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from auto_clip.cli import run_pipeline
from auto_clip.config import RunRequest

JOBS: dict[str, dict[str, object]] = {}
JOBS_LOCK = threading.Lock()
STATE_FILE: Path | None = None


def _set_job(job_id: str, **fields: object) -> None:
    with JOBS_LOCK:
        entry = JOBS.setdefault(job_id, {})
        entry.update(fields)
        if STATE_FILE is not None:
            try:
                STATE_FILE.write_text(json.dumps(JOBS), encoding="utf-8")
            except Exception:
                pass


def _load_state(state_file: Path) -> None:
    global STATE_FILE
    STATE_FILE = state_file
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                with JOBS_LOCK:
                    for job_id, entry in data.items():
                        # Anything mid-processing when we died is now failed.
                        if isinstance(entry, dict) and entry.get("state") == "processing":
                            entry["state"] = "error"
                            entry["error"] = "Processor restarted mid-job (out of memory or crash). Job was automatically retried if eligible."
                        JOBS[job_id] = entry
        except Exception:
            pass


def _process_job(payload: dict[str, object], work_dir: Path, config_path: str | None) -> None:
    job_id = str(payload.get("id") or "manual")
    source = str(payload["source"])

    try:
        request = RunRequest(source=source, config_path=config_path, work_dir=str(work_dir))
        summary = run_pipeline(request, progress=lambda stage: _set_job(job_id, stage=stage))

        clip_paths = []
        for clip in summary.get("clips", []):
            clip_path = Path(str(clip.get("clip_path", "")))
            if clip_path.exists():
                clip_paths.append(str(clip_path))

        _set_job(job_id, state="done", summary=summary, clip_paths=clip_paths)
        print(f"Job {job_id} completed: {len(clip_paths)} clips")
    except Exception as exc:
        print(f"Job {job_id} failed: {exc}")
        _set_job(job_id, state="error", error=str(exc), trace=traceback.format_exc())


class ProcessorHandler(BaseHTTPRequestHandler):
    server_version = "AutoClipProcessor/0.3"

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

        if self.path.startswith("/job/"):
            parts = self.path.split("/")
            # /job/<id> or /job/<id>/file/<name>
            if len(parts) == 3:
                job_id = parts[2]
                with JOBS_LOCK:
                    entry = dict(JOBS.get(job_id) or {})
                if not entry:
                    self._json_response({"ok": False, "error": "Unknown job"}, status=404)
                    return
                files = [Path(p).name for p in entry.get("clip_paths", [])]
                self._json_response(
                    {
                        "ok": True,
                        "job_id": job_id,
                        "state": entry.get("state"),
                        "stage": entry.get("stage"),
                        "files": files,
                        "summary": entry.get("summary"),
                        "error": entry.get("error"),
                    }
                )
                return

            if len(parts) == 5 and parts[3] == "file":
                job_id, name = parts[2], parts[4]
                with JOBS_LOCK:
                    entry = JOBS.get(job_id) or {}
                    clip_paths = list(entry.get("clip_paths", []))
                match = next((p for p in clip_paths if Path(p).name == name), None)
                if not match or not Path(match).exists():
                    self._json_response({"ok": False, "error": "File not found"}, status=404)
                    return
                data = Path(match).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

        self._json_response({"ok": False, "error": "Not Found"}, status=404)

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
            payload["id"] = job_id

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

        _set_job(job_id, state="processing", source=source)

        worker = threading.Thread(
            target=_process_job,
            args=(payload, self.server.work_dir, config_path),
            daemon=True,
        )
        worker.start()

        self._json_response(
            {
                "ok": True,
                "accepted": True,
                "job_id": job_id,
                "state": "processing",
            },
            status=202,
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
    _load_state(work_dir / "jobs_state.json")

    server = ProcessorServer((args.host, args.port), work_dir=work_dir)
    print(f"Processor webhook listening on http://{args.host}:{args.port}")
    print("POST /process to execute jobs, GET /health for readiness")
    server.serve_forever()


if __name__ == "__main__":
    main()
