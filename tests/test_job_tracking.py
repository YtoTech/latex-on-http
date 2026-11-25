import io
import json

import pytest
from flask import Flask

from latexonhttp.api import builds
from latexonhttp.docs import docs_app
from latexonhttp.sandbox import SandboxUnavailable

SUCCESS_OUTPUT = {
    "status": "ok",
    "error": None,
    "pdf": b"%PDF-test",
    "log_files": {},
    "output_path": "output.pdf",
    "duration": 0.25,
    "logs": "",
    "commands": [],
    "is_timeout": False,
}


class JobRecorder:
    def __init__(self):
        self.created = []
        self.updates = []

    def create(self, metadata):
        self.created.append(metadata)

    def update(self, job_id, **metadata):
        self.updates.append((job_id, metadata))

    @property
    def final(self):
        return self.updates[-1][1]


@pytest.fixture
def recorder(monkeypatch, tmp_path):
    recorded_jobs = JobRecorder()
    monkeypatch.setattr(builds, "create_job", recorded_jobs.create)
    monkeypatch.setattr(builds, "update_job", recorded_jobs.update)
    monkeypatch.setattr(builds, "latexToPdf", lambda *args: SUCCESS_OUTPUT)
    monkeypatch.setattr(
        builds, "forward_resource_to_cache", lambda _resource, _data: (True, None)
    )
    monkeypatch.setattr(
        "latexonhttp.workspaces.filesystem.WORKSPACE_DIRECTORY", str(tmp_path)
    )
    return recorded_jobs


def build_client():
    test_app = Flask(__name__)
    test_app.register_blueprint(builds.builds_app, url_prefix="/builds")
    # Registered (like in the real app) so error responses can build their
    # /docs/ documentation links via url_for.
    test_app.register_blueprint(docs_app)
    return test_app.test_client()


def json_body():
    return json.dumps(
        {"compiler": "pdflatex", "resources": [{"content": "private TeX"}]}
    ).encode()


def post_json(client, **kwargs):
    return client.post(
        "/builds/sync", data=json_body(), content_type="application/json", **kwargs
    )


def test_success_records_request_metadata_metrics_and_job_header(recorder):
    response = post_json(
        build_client(),
        headers={
            "User-Agent": "job-tracker-test",
            "X-Forwarded-For": "203.0.113.1, 2001:db8::2",
        },
        environ_overrides={"REMOTE_ADDR": "2001:db8::1"},
    )

    assert response.status_code == 201
    job = recorder.created[0]
    assert response.headers["X-Job-ID"] == job["id"]
    assert job["http_payload_size"] == len(json_body())
    assert job["input_spec_mode"] == "json"
    assert job["remote_ip"] == "2001:db8::1"
    assert job["forwarded_remote_ip"] == "203.0.113.1, 2001:db8::2"
    assert job["user_agent"] == "job-tracker-test"
    assert job["received_at"].tzinfo is not None
    assert job["cleaned_payload"]["resources"] == [{"content": True, "file": False}]
    assert "private TeX" not in repr(job["cleaned_payload"])
    assert recorder.final["job_status"] == "completed"
    assert recorder.final["error_code"] is None
    assert recorder.final["replied_at"] is not None
    compilation_metadata = recorder.updates[-2][1]
    assert compilation_metadata["output_type"] == "pdf"
    assert compilation_metadata["output_size"] == len(SUCCESS_OUTPUT["pdf"])
    assert compilation_metadata["ended_compiling_at"] is not None
    fetch_metadata = recorder.updates[1][1]
    assert fetch_metadata["fetched_resources_count"] == 1
    assert fetch_metadata["fetched_resources_size"] == len(b"private TeX")


def test_user_agent_is_none_and_get_body_size_is_zero(recorder):
    response = build_client().get(
        "/builds/sync",
        query_string={"content": "hello"},
        headers={"User-Agent": ""},
    )

    assert response.status_code == 201
    assert recorder.created[0]["user_agent"] == ""
    assert recorder.created[0]["http_payload_size"] == 0
    assert recorder.created[0]["input_spec_mode"] == "querystring"


def test_multipart_size_includes_full_binary_request_body(recorder):
    content = b"\\documentclass{article}\n" + bytes(range(256)) * 200
    boundary = "job-tracking-boundary"
    body = (
        f"--{boundary}\r\n".encode()
        + b'Content-Disposition: form-data; name="file1"; filename="main.tex"\r\n'
        + b"Content-Type: application/octet-stream\r\n\r\n"
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )

    response = build_client().post(
        "/builds/sync",
        data=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )

    assert response.status_code == 201
    job = recorder.created[0]
    assert len(body) > 32767
    assert job["http_payload_size"] == len(body)
    assert job["input_spec_mode"] == "multipart/form-data"
    assert job["cleaned_payload"]["resources"][0]["file"] is True


def test_malformed_request_does_not_create_a_job(recorder):
    response = build_client().post("/builds/sync", json={})

    assert response.status_code == 400
    assert recorder.created == []
    assert recorder.updates == []


def test_fetch_failure_is_terminal_and_keeps_partial_counts(recorder):
    response = build_client().post(
        "/builds/sync", json={"resources": [{"main": True, "file": "not-base64"}]}
    )

    assert response.status_code == 400
    assert response.headers["X-Job-ID"] == recorder.created[0]["id"]
    assert recorder.final["job_status"] == "errored"
    assert recorder.final["error_code"] == "INVALID_BASE64_CONTENT"
    assert recorder.updates[-2][1]["fetched_resources_count"] == 0
    assert all("compilation_hash" not in metadata for _, metadata in recorder.updates)


def test_cache_hits_are_counted_separately(recorder, monkeypatch):
    monkeypatch.setattr(
        builds, "get_resource_from_cache", lambda _resource: (True, b"cached data")
    )
    response = build_client().post(
        "/builds/sync", json={"resources": [{"cache": "sha256:test"}]}
    )

    assert response.status_code == 201
    fetch_metadata = recorder.updates[1][1]
    assert fetch_metadata["fetched_resources_count"] == 1
    assert fetch_metadata["fetched_resources_cache_hits"] == 1
    assert fetch_metadata["fetched_resources_cache_hits_size"] == len(b"cached data")


def test_sandbox_failure_closes_compilation_phase(recorder, monkeypatch):
    def fail_compilation(*_args):
        raise SandboxUnavailable("sandbox unavailable")

    monkeypatch.setattr(builds, "latexToPdf", fail_compilation)
    monkeypatch.setattr(
        builds, "report_sandbox_diagnostic", lambda *_args, **_kwargs: None
    )

    response = post_json(build_client())

    assert response.status_code == 503
    assert recorder.final["job_status"] == "errored"
    assert recorder.final["error_code"] == "SANDBOX_UNAVAILABLE"
    assert recorder.final["ended_compiling_at"] is not None


@pytest.mark.parametrize(
    ("is_timeout", "expected_error"),
    [(False, "COMPILATION_ERROR"), (True, "COMPILATION_TIMEOUT")],
)
def test_compilation_failure_is_terminal(
    recorder, monkeypatch, is_timeout, expected_error
):
    output = {
        **SUCCESS_OUTPUT,
        "status": "ko",
        "pdf": None,
        "logs": "LaTeX error",
        "is_timeout": is_timeout,
    }
    monkeypatch.setattr(builds, "latexToPdf", lambda *_args: output)

    response = post_json(build_client())

    assert response.status_code == 400
    assert recorder.final["job_status"] == "errored"
    assert recorder.final["error_code"] == expected_error
    assert recorder.updates[-2][1]["output_size"] is None


def test_unexpected_compilation_exception_is_tracked(recorder, monkeypatch):
    def fail_compilation(*_args):
        raise RuntimeError("unexpected compiler failure")

    monkeypatch.setattr(builds, "latexToPdf", fail_compilation)

    response = post_json(build_client())

    assert response.status_code == 500
    assert recorder.final["job_status"] == "errored"
    assert recorder.final["error_code"] == "SERVER_ERROR"
    assert recorder.final["ended_compiling_at"] is not None


def test_initial_insert_failure_prevents_compilation(recorder, monkeypatch):
    compilation_called = False

    def fail_insert(_metadata):
        raise RuntimeError("database unavailable")

    def compile_document(*_args):
        nonlocal compilation_called
        compilation_called = True
        return SUCCESS_OUTPUT

    monkeypatch.setattr(builds, "create_job", fail_insert)
    monkeypatch.setattr(builds, "latexToPdf", compile_document)

    response = post_json(build_client())

    assert response.status_code == 500
    assert response.get_json() == {"error": "SERVER_ERROR"}
    assert compilation_called is False
    assert "X-Job-ID" not in response.headers
    assert recorder.updates == []


def test_later_tracking_failure_does_not_replace_pdf(recorder, monkeypatch):
    def fail_update(_job_id, **_metadata):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(builds, "update_job", fail_update)

    response = post_json(build_client())

    assert response.status_code == 201
    assert response.data == SUCCESS_OUTPUT["pdf"]
    assert response.headers["X-Job-ID"] == recorder.created[0]["id"]


def test_compilation_hash_is_equal_across_json_and_multipart(recorder):
    json_resources = [
        {"path": "article.tex", "content": "private TeX", "main": True},
        {"path": "assets/data.txt", "file": "cGF5bG9hZA=="},
    ]
    response = build_client().post(
        "/builds/sync",
        json={
            "resources": json_resources,
            "options": {"compiler": {"silent": False}},
        },
    )
    assert response.status_code == 201
    json_hash = next(
        metadata["compilation_hash"]
        for _, metadata in recorder.updates
        if "compilation_hash" in metadata
    )

    recorder.updates.clear()
    multipart_resources = [
        {"path": "assets/data.txt", "multipart": "data_file"},
        {"path": "article.tex", "multipart": "main_file", "main": True},
    ]
    response = build_client().post(
        "/builds/sync",
        data={
            "resources": json.dumps(multipart_resources),
            "options.compiler.silent": "false",
            "data_file": (io.BytesIO(b"payload"), "ignored.bin"),
            "main_file": (io.BytesIO(b"private TeX"), "article.tex"),
        },
    )

    assert response.status_code == 201
    multipart_hash = next(
        metadata["compilation_hash"]
        for _, metadata in recorder.updates
        if "compilation_hash" in metadata
    )
    assert multipart_hash == json_hash
    assert len(json_hash) == 64
    assert [job["compilation_hash"] for job in recorder.created] == [None, None]


# -------------
# Usage scoring.
# -------------


def test_success_records_usage_scores(recorder):
    response = post_json(build_client())

    assert response.status_code == 201
    final = recorder.final
    # Outgoing data: the response body is the PDF.
    assert (
        final["response_size"] == len(response.get_data()) == len(SUCCESS_OUTPUT["pdf"])
    )
    # Incoming data: the whole request payload, in tokens.
    assert final["usage_score_incoming"] == round(len(json_body()) / 1024, 6)
    # Fetch: inline content is fetched, in tokens.
    assert final["usage_score_fetch"] == round(len(b"private TeX") / 1024, 6)
    # Processing: received-to-replied wall time.
    assert final["usage_score_processing"] > 0
    assert final["usage_score_outgoing"] == round(len(SUCCESS_OUTPUT["pdf"]) / 1024, 6)
    assert final["usage_score_total"] == pytest.approx(
        final["usage_score_incoming"]
        + final["usage_score_fetch"]
        + final["usage_score_processing"]
        + final["usage_score_outgoing"]
    )


def test_cache_hits_are_free_in_the_usage_score(recorder, monkeypatch):
    monkeypatch.setattr(
        builds, "get_resource_from_cache", lambda _resource: (True, b"cached data")
    )
    response = build_client().post(
        "/builds/sync", json={"resources": [{"cache": "sha256:test"}]}
    )

    assert response.status_code == 201
    assert recorder.final["usage_score_fetch"] == 0.0


def test_compilation_error_counts_the_error_body_as_outgoing(recorder, monkeypatch):
    output = {
        **SUCCESS_OUTPUT,
        "status": "ko",
        "pdf": None,
        "logs": "LaTeX error\n" * 100,
        "is_timeout": False,
    }
    monkeypatch.setattr(builds, "latexToPdf", lambda *_args: output)

    response = post_json(build_client())

    assert response.status_code == 400
    final = recorder.final
    assert final["response_size"] == len(response.get_data())
    assert final["usage_score_outgoing"] == round(len(response.get_data()) / 1024, 6)
    assert final["usage_score_incoming"] > 0
    assert final["usage_score_processing"] > 0
    assert final["usage_score_total"] > 0


def test_fetch_failure_still_scores_the_request(recorder):
    response = build_client().post(
        "/builds/sync", json={"resources": [{"main": True, "file": "not-base64"}]}
    )

    assert response.status_code == 400
    final = recorder.final
    # Nothing was fetched...
    assert final["usage_score_fetch"] == 0.0
    # ...but the payload was still received and occupied the server.
    assert final["usage_score_incoming"] > 0
    assert final["usage_score_processing"] > 0


def test_scoring_failure_does_not_take_the_job_update_down(recorder, monkeypatch):
    def fail_scoring(*_args):
        raise RuntimeError("scoring unavailable")

    monkeypatch.setattr(builds, "usage_scores", fail_scoring)

    response = post_json(build_client())

    assert response.status_code == 201
    final = recorder.final
    assert final["job_status"] == "completed"
    assert "usage_score_total" not in final
    assert response.headers["X-Job-ID"] == recorder.created[0]["id"]
