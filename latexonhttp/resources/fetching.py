"""
latexonhttp.resources.fetching
~~~~~~~~~~~~~~~~~~~~~
Fetchers for resources.

:copyright: (c) 2019 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import base64
import binascii
import logging
import os
import socket

import requests

from latexonhttp.resources.urlguard import (
    InvalidURLError,
    SSRFBlockedError,
    safe_get,
)
from latexonhttp.resources.utils import redact_resource_url

logger = logging.getLogger(__name__)

# ; # TODO Extract the filesystem management in a module:
# ; # - determine of fs/files actions to get to construct the filesystem;
# ; # - support content/string, base64/file, url/file, url/git, url/tar, post-data/tar
# ; # - hash and make a (deterministic) signature of files uploaded;
# ; # - from the list of actions, prepare the file system (giving only a root directory);
# ; # (- add a cache management on the file system preparation subpart).


def fetcher_utf8_string(resource, _get_from_cache):
    raw_string = resource["body_source"]["raw_string"]
    if not isinstance(raw_string, str):
        return (
            None,
            {
                "error": "INVALID_STRING_CONTENT",
                "message": "The resource content field must contain a string.",
                "fetch_error": {
                    "type": "invalid_content_type",
                    "content_type": type(raw_string).__name__,
                },
                "resource": resource,
            },
        )
    return raw_string.encode("utf-8"), None


def fetcher_base64_file(resource, _get_from_cache):
    try:
        return (
            base64.b64decode(resource["body_source"]["raw_base64"], validate=True),
            None,
        )
    except (binascii.Error, TypeError, ValueError) as exc:
        return (
            None,
            {
                "error": "INVALID_BASE64_CONTENT",
                "message": (
                    "The resource file field must contain valid Base64-encoded content."
                ),
                # Path of the resource in the build filesystem, so clients can
                # tell which uploaded file failed to decode.
                "path": resource.get("build_path"),
                "fetch_error": {
                    "type": "invalid_base64",
                    "exception_content": str(exc),
                },
                "resource": resource,
            },
        )


# In seconds.
# Configurable by environment, so we can - among other things - reduce the
# delay in test configuration (see docker-compose.test.yml).
FETCHER_HTTP_REQ_CONNECT_TIMEOUT = float(
    os.getenv("FETCHER_HTTP_REQ_CONNECT_TIMEOUT", 15)
)
FETCHER_HTTP_REQ_READ_TIMEOUT = float(os.getenv("FETCHER_HTTP_REQ_READ_TIMEOUT", 60))
# (Connect, read) timeouts.
HTTP_REQUEST_TIMEOUT = (FETCHER_HTTP_REQ_CONNECT_TIMEOUT, FETCHER_HTTP_REQ_READ_TIMEOUT)


def _invalid_url_message(invalid):
    """Human-readable explanation for an :class:`InvalidURLError`."""
    allowed = ", ".join(invalid.allowed_schemes) if invalid.allowed_schemes else None
    if invalid.reason == "no_scheme":
        base = "The resource URL has no scheme (e.g. https://example.com/main.tex)."
        if allowed:
            base += f" Allowed schemes: {allowed}."
        return base
    if invalid.reason == "unsupported_scheme":
        base = f"The resource URL scheme '{invalid.detail}' is not supported."
        if allowed:
            base += f" Allowed schemes: {allowed}."
        return base
    if invalid.reason == "missing_host":
        return "The resource URL has no host (e.g. https://example.com/main.tex)."
    if invalid.reason == "invalid_port":
        return "The resource URL port is invalid (must be between 0 and 65535)."
    return "The resource URL is malformed and cannot be fetched."


def fetcher_url_file(resource, _get_from_cache):
    url = resource["body_source"]["url"]
    logger.info("Fetching file from %s", redact_resource_url(url))
    try:
        # SSRF guard: validates the URL (scheme, host, resolved addresses) and
        # pins the connection to a validated address, re-checking every redirect.
        response = safe_get(url, HTTP_REQUEST_TIMEOUT)
        logger.info(
            "Fetch response %s of content length %d",
            response.status_code,
            len(response.content),
        )
        if response.status_code >= 300:
            return (
                None,
                {
                    "error": "RESOURCE_FETCH_FAILURE",
                    "fetch_error": {
                        "type": "http_error",
                        "http_code": response.status_code,
                        "http_response_content": response.text,
                    },
                    "resource": resource,
                },
            )
        return response.content, None
    except InvalidURLError as invalid:
        # An unfetchable URL (bad/missing scheme, no host, unparsable port) is a
        # client error, not a server fault, and not a security block. The
        # offending URL is echoed in resource.body_source.url.
        logger.info(
            "Rejected resource URL %s: %s", redact_resource_url(url), invalid.reason
        )
        fetch_error = {
            "type": "invalid_url",
            "reason": invalid.reason,
            "detail": invalid.detail,
            "http_code": None,
            "http_response_content": None,
        }
        if invalid.allowed_schemes:
            fetch_error["allowed_schemes"] = list(invalid.allowed_schemes)
        return (
            None,
            {
                "error": "RESOURCE_FETCH_FAILURE",
                "message": _invalid_url_message(invalid),
                "fetch_error": fetch_error,
                "resource": resource,
            },
        )
    except SSRFBlockedError as blocked:
        # A blocked URL is a client error (400), not a server fault. The detail
        # may name the offending host/address but never leaks internal state.
        logger.warning(
            "Blocked resource URL %s: %s", redact_resource_url(url), blocked.reason
        )
        return (
            None,
            {
                "error": "RESOURCE_FETCH_FAILURE",
                "fetch_error": {
                    "type": "ssrf_blocked",
                    "reason": blocked.reason,
                    "detail": blocked.detail,
                    "http_code": None,
                },
                "resource": resource,
            },
        )
    except socket.gaierror as gae:
        # A name that does not resolve is a plain fetch failure, not a block.
        return (
            None,
            {
                "error": "RESOURCE_FETCH_FAILURE",
                "fetch_error": {
                    "type": "connection_error",
                    "exception_content": str(gae),
                    "http_code": None,
                    "http_response_content": None,
                },
                "resource": resource,
            },
        )
    except requests.exceptions.Timeout as te:
        return (
            None,
            {
                "error": "RESOURCE_FETCH_FAILURE",
                "fetch_error": {
                    "type": "request_timeout",
                    "exception_content": str(te),
                    "http_code": None,
                    "http_response_content": None,
                },
                "resource": resource,
            },
        )
    except requests.exceptions.ConnectionError as cee:
        return (
            None,
            {
                "error": "RESOURCE_FETCH_FAILURE",
                "fetch_error": {
                    "type": "connection_error",
                    "exception_content": str(cee),
                    "http_code": None,
                    "http_response_content": None,
                },
                "resource": resource,
            },
        )
    except (
        requests.exceptions.InvalidSchema,
        requests.exceptions.InvalidURL,
        requests.exceptions.MissingSchema,
    ) as ue:
        return (
            None,
            {
                "error": "RESOURCE_FETCH_FAILURE",
                "message": "The resource URL is malformed and cannot be fetched.",
                "fetch_error": {
                    "type": "invalid_url",
                    "reason": "malformed_url",
                    "detail": str(ue),
                    "exception_content": str(ue),
                    "http_code": None,
                    "http_response_content": None,
                },
                "resource": resource,
            },
        )


def fetcher_hash_cache(resource, get_from_cache):
    if not get_from_cache:
        return None, "NO_CACHE_PROVIDER_ENABLED"
    logger.debug("Trying to fetch from cache %s", resource)
    is_ok, cached_data = get_from_cache(resource)
    if not is_ok:
        return None, "CACHE_PROCESS_ERROR"
    if not cached_data:
        return None, "CACHE_MISS"
    return cached_data, None


FETCHERS = {
    "utf8/string": fetcher_utf8_string,
    "base64/file": fetcher_base64_file,
    "url/file": fetcher_url_file,
    "hash/cache": fetcher_hash_cache,
    # TODO "url/git", "url/tar"
    # TODO Support a base64/gz/file, for compressed file upload?
}


def fetch_resources(resources, on_fetched, get_from_cache=None):
    """
    on_fetched(resource, data)
    get_from_cache(resource)
    """
    # TODO Fetch cache? (URL, git, etc.)
    # Managed by each fetcher, with options provided in input.
    # (No fetch cache by default)
    # TODO Passing options to fetcher:
    # (for eg. retries and follow_redirects for URL, encoding, etc.)
    # - default option dict;
    # - override by input.
    for resource in resources:
        resource_fetcher = FETCHERS.get(resource["type"])
        if not resource_fetcher:
            return {"error": "FETCH_METHOD_NOT_SUPPORTED", "method": resource["type"]}
        # Catch fetch error.
        fetched_data, fetch_error = resource_fetcher(resource, get_from_cache)
        if fetch_error:
            return fetch_error
        on_fetched_error = on_fetched(resource, fetched_data)
        if on_fetched_error:
            return on_fetched_error
