import pytest

from latexonhttp.resources.utils import prune_resources_content_for_logging


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
