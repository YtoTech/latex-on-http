# Copyright (C) 2017-2019 Yoan Tournade (upstream LaTeX-on-HTTP)
# Copyright (C) 2026 Inkmirage (Endleaf render worker modifications)
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run one job in a throwaway Podman container and classify the result."""

import json
import logging
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass

from colophon.cgroup_caps import CpuControllerMissing
from colophon.diagnostics import parse_stderr
from colophon.layout_map import parse_layout_map
from colophon.pdf_layout_check import parse_pdf_layout
from colophon.layout_warn import parse_layout
from colophon.enums import job_payload
from colophon.tex_log import parse_tex_warnings
from colophon.limits import (
    OUTPUT_CAP_BYTES,
    STDERR_KEEP_BYTES,
    SUPERVISOR_TIMEOUT_SEC,
    TIMEOUT_ELAPSED_FLOOR_SEC,
    WALL_SEC,
    allocation_failure,
)
from colophon.podman_args import (
    build_podman_kill_args,
    build_podman_rm_args,
    build_podman_run_args,
    ensure_rlimit_hook_dir,
    podman_supports_ulimit_as,
    probe_podman_version,
)

logger = logging.getLogger(__name__)


@dataclass
class Outcome:
    kind: str
    body: bytes = b""
    content_type: str = "application/json"
    detail: str = ""
    wall_sec: float | None = None
    memory_peak: int | None = None
    pids_peak: int | None = None
    memory_mode: str | None = None
    diagnostic: dict | None = None
    # ENDLEAF-R57-WARN. Present only when a count is above zero.
    tex_warnings: dict | None = None
    # ENDLEAF-R59-OVERHANG. layout_overhang warnings; empty when none.
    layout_warnings: tuple = ()
    # ENDLEAF-R60-LAYOUT. Encoded page layout map; None when absent.
    layout_map: str | None = None

    @property
    def ok(self):
        return self.kind == "ok"


def enforce_output_cap(payload, cap=OUTPUT_CAP_BYTES):
    """Return ``payload`` when it is within the cap, else raise ``ValueError``."""
    if len(payload) > cap:
        raise ValueError("output cap")
    return payload


def _marker(stderr):
    for line in stderr.splitlines():
        if line.startswith(b"ENDLEAF_STATUS "):
            return line.split(None, 1)[1].strip().decode("ascii", "replace")
    return None


def classify_result(
    *,
    returncode,
    timed_out,
    elapsed,
    capped,
    abort,
    stderr,
):
    """Map a finished sandbox to a fail-closed result kind.

    A wall-clock kill is ``failTimeout``, which is not a render error.
    The primary rule is the runner's own elapsed time: at or after the
    job timeout, every exit code is ``failTimeout``. Podman 4.3
    ``run --timeout`` exits 255 in that case. Exit 255 before the timeout
    is some other Podman error and stays a render error. A SIGKILL at the
    timeout floor (137 or -9) is the same wall-clock kill. Output over the
    cap, an earlier memory or pid kill, and an allocation failure
    (``RLIMIT_AS``) are ``failCapHit``.
    """
    marker = _marker(stderr or b"")
    at_job_timeout = elapsed >= WALL_SEC
    # Same threshold as the primary rule. Kept so a 255 is not treated as
    # a timeout unless the job has already used its wall clock.
    podman_timeout = returncode == 255 and elapsed >= WALL_SEC
    sigkill_wall = elapsed >= TIMEOUT_ELAPSED_FLOOR_SEC and returncode in (137, -9)
    if timed_out or at_job_timeout or podman_timeout or sigkill_wall:
        return "failTimeout"
    if abort:
        return "rejectKillSwitch"
    if capped or marker == "cap" or returncode == 11:
        return "failCapHit"
    if returncode in (137, -9):
        return "failCapHit"
    if returncode not in (0, None) and allocation_failure(stderr):
        return "failCapHit"
    if marker == "invalid" or returncode == 12:
        return "rejectInvalidInput"
    if returncode in (125, 126, 127) and marker is None:
        return "rejectSpawnFail"
    if marker == "render_error" or returncode == 10:
        return "rejectRenderError"
    if returncode == 0 and marker in (None, "ok"):
        return "ok"
    return "rejectRenderError"


def collect_process(proc, *, cap, timeout, kill):
    """Read stdout up to ``cap`` bytes. Over-cap output is discarded."""
    state = {"stdout": b"", "stderr": b"", "capped": False}

    def read_stdout():
        total = 0
        chunks = []
        while True:
            block = proc.stdout.read(65536)
            if not block:
                break
            total += len(block)
            if total > cap:
                state["capped"] = True
                state["stdout"] = b""
                try:
                    kill()
                except Exception:
                    logger.warning("kill during output cap failed")
                while proc.stdout.read(65536):
                    pass
                return
            chunks.append(block)
        state["stdout"] = b"".join(chunks)

    def read_stderr():
        buf = b""
        while True:
            block = proc.stderr.read(65536)
            if not block:
                break
            buf = (buf + block)[-STDERR_KEEP_BYTES:]
        state["stderr"] = buf

    out_thread = threading.Thread(target=read_stdout, daemon=True)
    err_thread = threading.Thread(target=read_stderr, daemon=True)
    out_thread.start()
    err_thread.start()
    timed_out = False
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            kill()
        except Exception:
            logger.warning("kill during wall clock failed")
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    out_thread.join(timeout=5)
    err_thread.join(timeout=5)
    if state["capped"]:
        state["stdout"] = b""
    return state["stdout"], state["stderr"], proc.returncode, timed_out, state["capped"]


class Supervisor:
    """One in-flight job per process. A second job is refused, not queued."""

    def __init__(self, runner, retry_after_sec):
        self._runner = runner
        self.retry_after_sec = retry_after_sec
        self._busy = threading.Lock()
        self._state = threading.Lock()
        self._name = None
        self._abort = threading.Event()

    def busy(self):
        return self._busy.locked()

    def submit(self, job):
        if not self._busy.acquire(blocking=False):
            return Outcome(kind="rejectBusy")
        self._abort.clear()
        name = f"endleaf-job-{uuid.uuid4().hex[:12]}"
        with self._state:
            self._name = name
        try:
            return self._runner(job, name, self._abort)
        finally:
            with self._state:
                self._name = None
            self._busy.release()

    def request_abort(self, kill_fn):
        """Kill the running container. Returns ``idle``, ``killed``, or ``kill_failed``."""
        with self._state:
            name = self._name
        if name is None:
            return "idle"
        self._abort.set()
        try:
            kill_fn(name)
        except Exception:
            logger.warning("podman kill failed for %s", name)
            return "kill_failed"
        return "killed"


def kill_container(podman, name):
    """SIGKILL the named job container. Does not list or touch any other container."""
    _podman_kill(podman, name)


def _podman_kill(podman, name):
    subprocess.run(
        build_podman_kill_args(podman=podman, name=name),
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _podman_rm(podman, name):
    subprocess.run(
        build_podman_rm_args(podman=podman, name=name),
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def make_podman_runner(config, switch):
    """Return a runner bound to this worker's image, token-free sandbox, and switch."""
    podman_version = probe_podman_version(config.podman)
    hooks_dir = None
    if not podman_supports_ulimit_as(podman_version):
        hooks_dir = ensure_rlimit_hook_dir()
        logger.warning(
            "podman %s rejects --ulimit as=; injecting RLIMIT_AS with a precreate hook",
            ".".join(str(part) for part in podman_version),
        )

    def kill_name(name):
        _podman_kill(config.podman, name)

    def watch(name, abort_event, done):
        while not done.wait(1):
            state = switch.read()
            if state.blocks_jobs:
                abort_event.set()
                kill_name(name)
                return

    def runner(job, name, abort_event):
        if switch.read().blocks_jobs:
            return Outcome(kind="rejectKillSwitch")
        # ENDLEAF-R56-WIRE. Every parsed field reaches the sandbox parse.
        payload = json.dumps(job_payload(job)).encode("utf-8")
        try:
            args = build_podman_run_args(
                podman=config.podman,
                image=config.image,
                name=name,
                as_bytes=config.rlimit_as_bytes,
                podman_version=podman_version,
                hooks_dir=hooks_dir,
            )
        except CpuControllerMissing:
            logger.error(
                "refusing to start job %s: cpu controller is not available",
                name,
            )
            return Outcome(kind="rejectSpawnFail", detail="cpu-controller")
        started = time.monotonic()
        done = threading.Event()
        watcher = threading.Thread(
            target=watch, args=(name, abort_event, done), daemon=True
        )
        watcher.start()
        try:
            try:
                proc = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except OSError as exc:
                logger.warning("podman spawn failed: %s", exc.__class__.__name__)
                return Outcome(kind="rejectSpawnFail", detail="spawn")
            try:
                proc.stdin.write(payload)
                proc.stdin.close()
            except BrokenPipeError:
                pass
            stdout, stderr, code, timed_out, capped = collect_process(
                proc,
                cap=OUTPUT_CAP_BYTES,
                timeout=SUPERVISOR_TIMEOUT_SEC,
                kill=lambda: kill_name(name),
            )
            elapsed = time.monotonic() - started
            meters, diagnostic = parse_stderr(stderr)
            kind = classify_result(
                returncode=code,
                timed_out=timed_out,
                elapsed=elapsed,
                capped=capped,
                abort=abort_event.is_set(),
                stderr=stderr,
            )
            if kind == "ok":
                try:
                    enforce_output_cap(stdout)
                except ValueError:
                    kind = "failCapHit"
            if kind != "ok" or not stdout:
                if kind == "ok":
                    kind = "rejectRenderError"
                logger.info(
                    "job %s lane=%s format=%s result=%s",
                    name,
                    job.lane,
                    job.output_format,
                    kind,
                )
                return Outcome(
                    kind=kind,
                    detail=kind,
                    wall_sec=round(elapsed, 3),
                    memory_peak=meters.get("memoryPeak"),
                    pids_peak=meters.get("pidsPeak"),
                    memory_mode=meters.get("memoryMode"),
                    diagnostic=(
                        diagnostic
                        if kind in ("rejectRenderError", "failCapHit")
                        else None
                    ),
                )
            logger.info(
                "job %s lane=%s format=%s result=ok bytes=%d",
                name,
                job.lane,
                job.output_format,
                len(stdout),
            )
            return Outcome(
                kind="ok",
                body=stdout,
                content_type=job.content_type,
                wall_sec=round(elapsed, 3),
                memory_peak=meters.get("memoryPeak"),
                pids_peak=meters.get("pidsPeak"),
                memory_mode=meters.get("memoryMode"),
                tex_warnings=parse_tex_warnings(stderr),
                layout_warnings=tuple(parse_layout(stderr)) + tuple(parse_pdf_layout(stderr)),
                layout_map=parse_layout_map(stderr),
            )
        finally:
            done.set()
            watcher.join(timeout=2)
            _podman_rm(config.podman, name)

    return runner
