import pytest

from latexonhttp.resources.utils import (
    prune_resources_content_for_logging,
    sanitize_input_spec_for_job,
)


@pytest.mark.parametrize("resources", [None, "not a list", 42, ["raw", 42]])
def test_resource_logging_tolerates_malformed_shapes(resources):
    input_spec = {"resources": resources}

    assert prune_resources_content_for_logging(input_spec)["resources"] == resources


def test_resource_logging_redacts_dictionary_content():
    input_spec = {
        "resources": [
            {"main": True, "content": "private TeX source"},
            {"path": "image.png", "file": "private base64"},
        ]
    }

    logged_spec = prune_resources_content_for_logging(input_spec)

    assert logged_spec["resources"] == [
        {"main": True, "content": True, "file": False},
        {"path": "image.png", "content": False, "file": True},
    ]
    assert "private" not in repr(logged_spec)


def test_job_payload_redacts_resource_contents_and_sensitive_url_parts():
    input_spec = {
        "resources": [
            {"content": "private TeX source"},
            {"file": "private Base64 source"},
            {"url": "https://user:password@example.com/main.tex?token=secret#private"},
        ]
    }

    cleaned_spec = sanitize_input_spec_for_job(input_spec)

    assert cleaned_spec["resources"] == [
        {"content": True, "file": False},
        {"content": False, "file": True},
        {"content": False, "file": False, "url": "https://example.com/main.tex"},
    ]
    assert input_spec["resources"][0]["content"] == "private TeX source"
    assert "password" not in repr(cleaned_spec)
    assert "token" not in repr(cleaned_spec)


def test_job_payload_does_not_fail_on_malformed_urls():
    cleaned_spec = sanitize_input_spec_for_job(
        {"resources": [{"url": "https://example.com:invalid/main.tex"}]}
    )

    assert cleaned_spec["resources"][0]["url"] == "<invalid-url>"
