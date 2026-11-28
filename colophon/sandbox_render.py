# Copyright (C) 2017-2019 Yoan Tournade (upstream LaTeX-on-HTTP)
# Copyright (C) 2026 Inkmirage (Endleaf render worker modifications)
# SPDX-License-Identifier: AGPL-3.0-or-later
"""In-container render. Stdout is the artifact; nothing is kept afterwards."""

import json
import os
import subprocess
import sys
from pathlib import Path

from colophon.diagnostics import first_tex_error, relocate_to_body
from colophon.enums import JobRejected, parse_job
from colophon.limits import OUTPUT_CAP_BYTES
from colophon.pdf_pages import fulldoc_page_count, fulldoc_page_failure
from colophon.settings import setting
from colophon.layout_map import label_fit_line, layout_map_line, page_blocks, page_marks
from colophon.layout_warn import final_pass, layout_line, layout_warnings, shell_pages
from colophon.tex_log import count_tex_warnings, tex_warn_line
from colophon.templates import compose_with_body_line
from colophon.render_plan import RenderPlanError, build_render_plan


def _status(name):
    sys.stderr.write(f"ENDLEAF_STATUS {name}\n")
    sys.stderr.flush()


def _read_int(paths):
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError:
            continue
        token = text.strip().split()
        if token and token[0].isdigit():
            return int(token[0])
    return None


def _memory_mode():
    """``cgroup`` when the launcher applied ``--memory``, else ``rlimit``.

    The launcher sets ``ENDLEAF_MEMORY_MODE``. ``COLOPHON_MEMORY_MODE`` is
    still read. A direct sandbox run with neither set falls back to the
    container's own controller list.
    """
    raw, _name = setting(os.environ, "MEMORY_MODE", default="")
    if raw in ("cgroup", "rlimit"):
        return raw
    try:
        text = Path("/sys/fs/cgroup/cgroup.controllers").read_text(encoding="utf-8")
    except OSError:
        return "rlimit"
    if "memory" in text.split():
        return "cgroup"
    return "rlimit"


def _emit_meters():
    payload = {
        "memoryPeak": _read_int(
            (
                "/sys/fs/cgroup/memory.peak",
                "/sys/fs/cgroup/memory/memory.max_usage_in_bytes",
            )
        ),
        "pidsPeak": _read_int(("/sys/fs/cgroup/pids.peak",)),
        "memoryMode": _memory_mode(),
    }
    sys.stderr.write(
        "ENDLEAF_METERS " + json.dumps(payload, separators=(",", ":")) + "\n"
    )
    sys.stderr.flush()


def _emit_diag(diagnostic):
    if not diagnostic:
        return
    sys.stderr.write(
        "ENDLEAF_DIAG " + json.dumps(diagnostic, separators=(",", ":")) + "\n"
    )
    sys.stderr.flush()


def _collect_logs():
    chunks = []
    for path in sorted(Path("/tmp").glob("*.log")):
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(chunks)


def _wrap_tex(template_id, lane, body, page_size="a4", orientation=None, label_size=None):
    """``(job.tex text, body start line)`` (ENDLEAF-R58-BODYLINE)."""
    try:
        return compose_with_body_line(
            template_id, lane, body, page_size=page_size, orientation=orientation, label_size=label_size
        )
    except (OSError, ValueError) as exc:
        raise RenderPlanError("wrapper") from exc


def _run(command):
    # Job files live in /tmp. TeX is given a relative name, so the engine
    # must be started there. openin_any=p refuses an absolute input path.
    completed = subprocess.run(
        command,
        cwd="/tmp",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        sys.stderr.buffer.write(completed.stdout[-8192:])
        raise RenderPlanError("command")
    return completed.stdout


def _pdf_layout_check(job, data, log, body_start, body_lines):
    """ENDLEAF-R81. Warn-only read of the finished PDF; it never changes the status.

    ``log`` is the final pass's TeX log (for Markdown, Pandoc's last LaTeX run). Findings go
    out as one ENDLEAF_PDFLAYOUT stderr line; guard and off-page counts go to the worker log.
    """
    try:
        from colophon.overfull import overfull_rows
        from colophon.pdf_layout_check import PDF_LOG_PREFIX, check_pdf, pdf_layout_line

        warnings = layout_warnings(log)
        rows, _ = overfull_rows(log, body_start=body_start, body_lines=body_lines)
        named = {row["page"] for row in rows if "page" in row}
        named |= {item["page"] for item in warnings if isinstance(item.get("page"), int)}
        result = check_pdf(
            data,
            template_id=job.template_id,
            blocks=page_blocks(log),
            marks=page_marks(log) if job.template_id == "fulldoc" else None,
            shell_pages=shell_pages(log),
            tex_pages=named,
        )
        for line in result.log_lines:
            sys.stderr.write(PDF_LOG_PREFIX + line + "\n")
        line = pdf_layout_line(result.items)
        if line is not None:
            sys.stderr.write(line + "\n")
    except Exception:  # warn-only: a failed check never fails the render
        sys.stderr.write("ENDLEAF_PDFLOG pdfcheck error\n")


def render_to_stdout(payload_bytes):
    plan = None
    body_start = None
    body_lines = 0
    data = b""
    status = "invalid"
    diagnostic = None
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
        job = parse_job(payload)
        plan = build_render_plan(job)
    except (UnicodeError, json.JSONDecodeError, JobRejected, RenderPlanError):
        status = "invalid"
    else:
        try:
            for path, content in plan.files.items():
                if content is None:
                    continue
                Path(path).write_text(content, encoding="utf-8")
            if job.input_kind == "tex" and job.output_format == "pdf":
                wrapped, body_start = _wrap_tex(
                    job.template_id,
                    job.lane,
                    job.source,
                    job.page_size,
                    job.orientation,
                    job.label_size,
                )
                body_lines = len(job.source.split("\n"))
                Path("/tmp/job.tex").write_text(wrapped, encoding="utf-8")
            output = b""
            for command in plan.commands:
                output = _run(list(command))
            data = Path(plan.output_path).read_bytes()
            log = _collect_logs()
            status = "cap" if len(data) > OUTPUT_CAP_BYTES else "ok"
            # ENDLEAF-R39-CAPS. Count after a successful compile. The gate
            # does not count pages. The message is the tool-result text.
            if status == "ok" and job.template_id == "fulldoc":
                failure = fulldoc_page_failure(fulldoc_page_count(data, log))
                if failure:
                    diagnostic = {
                        "engine": "tex",
                        "message": failure,
                        "file": "job.tex",
                        "line": None,
                        "fence": None,
                    }
                    # Unreadable is a render error. Over the cap is failCapHit.
                    status = "render_error" if "unreadable" in failure else "cap"
                else:
                    # The fixture asserts this. The log is deleted below.
                    overfull = log.count("Overfull \\hbox")
                    sys.stderr.write(f"ENDLEAF_OVERFULL {overfull}\n")
            # ENDLEAF-R70-SHELL. A Markdown PDF: the fence fit lines come from
            # Pandoc's --verbose output (its last LaTeX run).
            if (
                status == "ok"
                and job.input_kind == "markdown"
                and job.output_format == "pdf"
            ):
                layout = layout_line(layout_warnings(final_pass(output)))
                if layout is not None:
                    sys.stderr.write(layout + "\n")
            # ENDLEAF-R57-WARN. Counts only, and only for the TeX path:
            # Pandoc compiles in its own directory, so /tmp has no log.
            if (
                status == "ok"
                and job.input_kind == "tex"
                and job.output_format == "pdf"
            ):
                line = tex_warn_line(count_tex_warnings(log))
                if line is not None:
                    sys.stderr.write(line + "\n")
                # ENDLEAF-R59-OVERHANG. A picture past its text line.
                layout = layout_line(layout_warnings(log))
                if layout is not None:
                    sys.stderr.write(layout + "\n")
                # ENDLEAF-R60-LAYOUT. Only fulldoc bodies carry marks.
                # ENDLEAF-R64-ROWS. Every TeX template sends its overfull rows.
                aux = None
                if job.template_id == "fulldoc":
                    try:
                        aux = Path("/tmp/job.aux").read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        aux = None
                # ENDLEAF-R66-FIT. A stocklabel job sends its labelFit map instead: the
                # runner reads one map per job, and label fit is the label's check.
                if job.template_id == "stocklabel":
                    mapping = label_fit_line(log)
                else:
                    mapping = layout_map_line(
                        log, body_start=body_start, body_lines=body_lines, aux=aux, source=job.source
                    )
                if mapping is not None:
                    sys.stderr.write(mapping + "\n")
            # ENDLEAF-R81. PDF jobs only, after the final pass, before the PDF is returned.
            if status == "ok" and job.output_format == "pdf":
                if job.input_kind == "tex":
                    _pdf_layout_check(job, data, log, body_start, body_lines)
                else:
                    _pdf_layout_check(job, data, final_pass(output), None, 0)
        except (OSError, RenderPlanError):
            diagnostic = relocate_to_body(
                first_tex_error(_collect_logs()), body_start, body_lines
            )
            status = "render_error"
        finally:
            paths = list(plan.files) + [plan.output_path, "/tmp/job.tex"]
            for pattern in ("*.log", "*.aux", "*.out", "*.toc", "*.xdv"):
                paths.extend(str(path) for path in Path("/tmp").glob(pattern))
            for path in paths:
                try:
                    Path(path).unlink()
                except OSError:
                    pass
    _emit_meters()
    if diagnostic and status in ("render_error", "cap"):
        _emit_diag(diagnostic)
    _status(status)
    if status == "ok":
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        return 0
    if status == "cap":
        return 11
    if status == "render_error":
        return 10
    return 12


def main():
    raw = sys.stdin.buffer.read()
    code = render_to_stdout(raw)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
