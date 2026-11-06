"""Authenticated API that runs student Python in disposable Docker containers."""
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
import hmac
import os
import re
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

MAX_CODE_CHARS = 20_000
MAX_OUTPUT_CHARS = 20_000
MAX_TIMEOUT_SECONDS = 10
MAX_REQUEST_BYTES = 100 * 1024
MAX_CONCURRENT_RUNS = max(1, min(int(os.getenv("MAX_CONCURRENT_RUNS", "2")), 8))
MAX_RUNS_PER_SESSION_PER_MINUTE = max(1, min(int(os.getenv("MAX_RUNS_PER_SESSION_PER_MINUTE", "20")), 120))
MAX_RUNS_PER_MINUTE = max(1, min(int(os.getenv("MAX_RUNS_PER_MINUTE", "120")), 1000))
RUNNER_IMAGE = os.getenv("CODE_RUNNER_IMAGE", "practise-python-runner:1")
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
_rate_lock = threading.Lock()
_session_runs: dict[str, deque[float]] = defaultdict(deque)
_all_runs: deque[float] = deque()
_reaper_task: asyncio.Task | None = None

app = FastAPI(title="Practise Code Executor", docs_url=None, redoc_url=None, openapi_url=None)


class RequestSizeLimitMiddleware:
    """Reject oversized execution payloads before JSON parsing allocates them."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("path") != "/execute":
            await self.application(scope, receive, send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            body.extend(message.get("body", b""))
            if len(body) > MAX_REQUEST_BYTES:
                response = JSONResponse({"detail": "Request is too large"}, status_code=413)
                await response(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay_body():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.application(scope, replay_body, send)


app.add_middleware(RequestSizeLimitMiddleware)


class ExecutionRequest(BaseModel):
    code: str = Field(min_length=1, max_length=MAX_CODE_CHARS)
    timeout_seconds: int = Field(default=5, ge=1, le=MAX_TIMEOUT_SECONDS)
    network: Literal[False] = False
    max_output_chars: int = Field(default=MAX_OUTPUT_CHARS, ge=1, le=MAX_OUTPUT_CHARS)
    session_id: uuid.UUID | None = None


def _expected_token() -> str:
    token = os.getenv("CODE_EXECUTOR_TOKEN", "")
    if len(token) < 32:
        raise HTTPException(status_code=503, detail="Executor is not configured")
    return token


def _authorize(authorization: str | None) -> None:
    token = _expected_token()
    prefix = "Bearer "
    supplied = authorization[len(prefix):] if authorization and authorization.startswith(prefix) else ""
    if not supplied or not hmac.compare_digest(supplied, token):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _check_rate_limit(session_id: uuid.UUID | None) -> None:
    """Limit runs per anonymous session to avoid monopolizing the executor."""
    key = str(session_id) if session_id else "unknown-session"
    now = time.monotonic()
    with _rate_lock:
        while _all_runs and now - _all_runs[0] >= 60:
            _all_runs.popleft()
        if len(_all_runs) >= MAX_RUNS_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Executor request limit reached")
        recent = _session_runs[key]
        while recent and now - recent[0] >= 60:
            recent.popleft()
        if len(recent) >= MAX_RUNS_PER_SESSION_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Execution rate limit reached")
        _all_runs.append(now)
        recent.append(now)
        # Bound memory for one service process with many one-off session IDs.
        if len(_session_runs) > 10_000:
            expired = [session for session, times in _session_runs.items()
                       if not times or now - times[-1] >= 60]
            for session in expired:
                _session_runs.pop(session, None)


def _force_remove(container_name: str) -> None:
    """Ensure a timed-out Docker CLI cannot leave its workload running."""
    try:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=3, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _reap_stale_containers() -> None:
    """Remove abandoned jobs after an executor restart or interrupted request."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--quiet", "--filter", "label=practise.managed=true"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return
    now = datetime.now(timezone.utc)
    for container_id in result.stdout.splitlines():
        try:
            inspected = subprocess.run(
                ["docker", "inspect", "--format={{.State.StartedAt}}", container_id],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=3, check=False,
            )
            started_at = datetime.fromisoformat(inspected.stdout.strip().replace("Z", "+00:00"))
            if inspected.returncode == 0 and (now - started_at).total_seconds() > 45:
                _force_remove(container_id)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            continue


async def _reaper_loop() -> None:
    while True:
        await asyncio.sleep(15)
        await asyncio.to_thread(_reap_stale_containers)


def _execute_container(code: str, timeout_seconds: int, output_limit: int) -> dict:
    """Run one Python process with no network, host mounts, or writable root FS."""
    container_name = f"practise-run-{uuid.uuid4().hex}"
    command = [
        "docker", "run", "--rm", "--interactive", "--name", container_name,
        "--label=practise.managed=true",
        "--pull=never", "--network=none", "--read-only", "--user=10001:10001",
        "--memory=128m", "--memory-swap=128m", "--cpus=0.5", "--pids-limit=32",
        "--cap-drop=ALL", "--security-opt=no-new-privileges:true",
        "--ulimit=cpu=3:3", "--ulimit=fsize=1048576:1048576", "--ulimit=nofile=64:64",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=8m",
        RUNNER_IMAGE, "python", "-I", "-S", "-",
    ]
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    except OSError:
        return {"status": "error", "output": "The isolated runner is unavailable."}

    captured = bytearray()
    output_exceeded = threading.Event()

    def read_output() -> None:
        assert process.stdout is not None
        while True:
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            remaining = output_limit - len(captured)
            if remaining > 0:
                captured.extend(chunk[:remaining])
            if len(chunk) > remaining:
                output_exceeded.set()
                try:
                    process.kill()
                except OSError:
                    pass
                break

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    timed_out = False
    try:
        assert process.stdin is not None
        try:
            process.stdin.write(code.encode("utf-8"))
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        try:
            return_code = process.wait(timeout=timeout_seconds + 2)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            return_code = process.wait(timeout=2)
        reader.join(timeout=2)
        if timed_out or output_exceeded.is_set():
            _force_remove(container_name)
        output = captured.decode("utf-8", errors="replace")[:output_limit]
        if timed_out:
            return {"status": "timeout", "output": "Execution timed out."}
        if output_exceeded.is_set():
            return {"status": "error", "output": "Execution output exceeded the limit."}
        if return_code != 0:
            # Expose only a one-line Python diagnostic, never Docker output or tracebacks.
            lines = output.splitlines()
            diagnostic = lines[-1].strip() if lines else ""
            if (len(diagnostic) <= 360
                    and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception): [^\r\n]+", diagnostic)):
                return {"status": "error", "output": diagnostic}
            return {"status": "error", "output": "The code could not be run."}
        return {"status": "ok", "output": output}
    finally:
        if process.poll() is None:
            process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            _force_remove(container_name)
        reader.join(timeout=1)
        if process.stdin:
            process.stdin.close()
        if process.stdout:
            process.stdout.close()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict:
    _expected_token()
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", RUNNER_IMAGE],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None
    if result is None or result.returncode != 0:
        raise HTTPException(status_code=503, detail="Runner image is unavailable")
    return {"status": "ready"}


@app.on_event("startup")
async def start_reaper() -> None:
    global _reaper_task
    _reaper_task = asyncio.create_task(_reaper_loop())


@app.on_event("shutdown")
async def stop_reaper() -> None:
    if _reaper_task:
        _reaper_task.cancel()


@app.post("/execute")
async def execute(payload: ExecutionRequest, authorization: str | None = Header(default=None)) -> dict:
    _authorize(authorization)
    _check_rate_limit(payload.session_id)
    if _semaphore.locked():
        raise HTTPException(status_code=429, detail="Runner is busy")
    async with _semaphore:
        return await asyncio.to_thread(
            _execute_container, payload.code, payload.timeout_seconds, payload.max_output_chars,
        )
