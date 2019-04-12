import subprocess
import re
import datetime
from operator import is_not
from functools import partial

# --------------------
# Package listing
# --------------------

TLMGR_LIST_LINE_REGEX_PATTERN = r"^(i|\s)\s(\S+):\s(.+)$"
TLMGR_LIST_LINE_REGEX = re.compile(TLMGR_LIST_LINE_REGEX_PATTERN)


def parse_tlmgr_list_line(line):
    regex_match = TLMGR_LIST_LINE_REGEX.match(line)
    if not regex_match:
        raise RuntimeError("Unable to parse tlmr list line ouput: {}".format(line))
    return {
        "installed": regex_match.group(1) == "i",
        "name": regex_match.group(2),
        "shortdesc": regex_match.group(3),
    }


def parse_tlmgr_list(output):
    return [parse_tlmgr_list_line(line) for line in output.splitlines()]


def list_packages(only_installed=False):
    cmd = ["tlmgr", "list"]
    if only_installed:
        cmd.append("--only-installed")
    cmd_output = subprocess.run(
        cmd, stdout=subprocess.PIPE, check=True, encoding="utf-8"
    )
    # cmd_output = subprocess.run(cmd, capture_output=True, check=True, encoding="utf-8")
    return parse_tlmgr_list(cmd_output.stdout)


def list_installed_packages():
    return list_packages(only_installed=True)


# --------------------
# Package info
# --------------------

TLMGR_INFO_LINE_REGEX_PATTERN = r"^(\S+):\s+(.+)$"
TLMGR_INFO_LINE_REGEX = re.compile(TLMGR_INFO_LINE_REGEX_PATTERN)

TLMGR_INFO_VALUE_PARSER_BOOLEAN = lambda value: value.lower() == "yes"
TLMGR_INFO_VALUE_PARSER_STRING_LIST = lambda value: value.split(" ")


def TLMGR_INFO_VALUE_PARSER_DATETIME(value):
    return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")


def TLMGR_INFO_VALUE_PARSER_SIZES(value):
    sizes_parts = value.split(",")
    return {
        key.replace(":", ""): value
        for (key, value) in [size_parts.split() for size_parts in sizes_parts]
    }


TLMGR_INFO_VALUE_PARSERS = {
    "installed": TLMGR_INFO_VALUE_PARSER_BOOLEAN,
    "relocatable": TLMGR_INFO_VALUE_PARSER_BOOLEAN,
    "cat-date": TLMGR_INFO_VALUE_PARSER_DATETIME,
    "cat-topics": TLMGR_INFO_VALUE_PARSER_STRING_LIST,
    "sizes": TLMGR_INFO_VALUE_PARSER_SIZES,
}


def parse_tlmgr_info_value(key, value):
    parser = TLMGR_INFO_VALUE_PARSERS.get(key, lambda value: value)
    return parser(value)


def extract_tlmgr_info_line(line):
    if not line:
        return None
    regex_match = TLMGR_INFO_LINE_REGEX.match(line)
    if not regex_match:
        raise RuntimeError("Unable to parse tlmr info line ouput: {}".format(line))
    return (regex_match.group(1), regex_match.group(2))


def parse_tlmgr_info(output):
    if "cannot find package" in output:
        return None
    return {
        key: parse_tlmgr_info_value(key, value)
        for (key, value) in filter(
            partial(is_not, None),
            [extract_tlmgr_info_line(line) for line in output.splitlines()],
        )
    }

    return [parse_tlmgr_list_line(line) for line in output.splitlines()]
    return output


def get_package_info(package_name):
    cmd_output = subprocess.run(
        ["tlmgr", "info", package_name],
        stdout=subprocess.PIPE,
        check=True,
        encoding="utf-8",
    )
    return parse_tlmgr_info(cmd_output.stdout)


# --------------------
# Utils
# --------------------


def get_ctan_link(package_name):
    return "https://ctan.org/pkg/{}".format(package_name)
