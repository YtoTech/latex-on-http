from latexonhttp.resources.utils import (
    compute_compilation_hash,
    process_resource_data_spec,
)


def resource_inputs():
    return [
        {
            "build_path": "__main_document__.tex",
            "is_main_document": True,
            "data_spec": process_resource_data_spec(b"private TeX"),
            "type": "utf8/string",
            "body_source": {"raw_string": "private TeX"},
        },
        {
            "build_path": "assets/data.txt",
            "is_main_document": False,
            "data_spec": process_resource_data_spec(b"payload"),
            "type": "base64/file",
            "body_source": {"raw_base64": "cGF5bG9hZA=="},
        },
    ]


def compilation_options():
    return {
        "compiler": {"silent": False, "force": True},
        "response": {"log_files_on_failure": True, "commands": False},
    }


def test_compilation_hash_ignores_resource_order_source_and_option_key_order():
    reordered_resources = [
        {
            **resource_inputs()[1],
            "type": "hash/cache",
            "body_source": {"hash": "sha256:any"},
        },
        {
            **resource_inputs()[0],
            "type": "base64/file",
            "body_source": {"raw_base64": "cHJpdmF0ZSBUZVg="},
        },
    ]
    reordered_options = {
        "response": {"commands": False, "log_files_on_failure": True},
        "compiler": {"force": True, "silent": False},
    }

    hash_a = compute_compilation_hash(
        "pdflatex", compilation_options(), resource_inputs()
    )
    hash_b = compute_compilation_hash(
        "pdflatex", reordered_options, reordered_resources
    )

    assert hash_a == hash_b
    assert len(hash_a) == 64
    int(hash_a, 16)


def test_compilation_hash_changes_with_actual_compilation_inputs():
    baseline = compute_compilation_hash(
        "pdflatex", compilation_options(), resource_inputs()
    )
    changed_resources = resource_inputs()
    changed_resources[1]["data_spec"] = process_resource_data_spec(b"changed")
    changed_path = resource_inputs()
    changed_path[1]["build_path"] = "assets/other.txt"
    changed_options = compilation_options()
    changed_options["compiler"]["silent"] = True

    assert (
        compute_compilation_hash("pdflatex", compilation_options(), changed_resources)
        != baseline
    )
    assert (
        compute_compilation_hash("pdflatex", compilation_options(), changed_path)
        != baseline
    )
    assert (
        compute_compilation_hash("pdflatex", changed_options, resource_inputs())
        != baseline
    )
    assert (
        compute_compilation_hash("xelatex", compilation_options(), resource_inputs())
        != baseline
    )
