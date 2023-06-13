# -*- coding: utf-8 -*-
"""
    latexonhttp.resources.fetching
    ~~~~~~~~~~~~~~~~~~~~~
    Fetchers for resources.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import base64
import requests
import logging

logger = logging.getLogger(__name__)

# ; # TODO Extract the filesystem management in a module:
# ; # - determine of fs/files actions to get to construct the filesystem;
# ; # - support content/string, base64/file, url/file, url/git, url/tar, post-data/tar
# ; # - hash and make a (deterministic) signature of files uploaded;
# ; # - from the list of actions, prepare the file system (giving only a root directory);
# ; # (- add a cache management on the file system preparation subpart).


def fetcher_utf8_string(resource, _get_from_cache):
    # TODO encode useful? Why we got an str here instead of unicode?
    return resource["body_source"]["raw_string"].encode("utf-8"), None


def fetcher_base64_file(resource, _get_from_cache):
    return base64.b64decode(resource["body_source"]["raw_base64"]), None


# TODO Make it configurable.
# (So we can - around other things - reduce the delay in test configuration)
HTTP_REQUEST_TIMEOUT = (15, 60)


def fetcher_url_file(resource, _get_from_cache):
    url = resource["body_source"]["url"]
    logger.info("Fetching file from %s", url)
    try:
        response = requests.get(url, timeout=HTTP_REQUEST_TIMEOUT)
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
