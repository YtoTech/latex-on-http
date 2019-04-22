# -*- coding: utf-8 -*-
"""
    latexonhttp.resources.fetching
    ~~~~~~~~~~~~~~~~~~~~~
    Fetchers for resources.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import base64
import urllib
import logging

logger = logging.getLogger(__name__)

# ; # TODO Extract the filesystem management in a module:
# ; # - determine of fs/files actions to get to construct the filesystem;
# ; # - support content/string, base64/file, url/file, url/git, url/tar, post-data/tar
# ; # - hash and make a (deterministic) signature of files uploaded;
# ; # - from the list of actions, prepare the file system (giving only a root directory);
# ; # (- add a cache management on the file system preparation subpart).


def fetcher_utf8_string(resource):
    # TODO encode useful? Why we got an str here instead of unicode?
    return resource["body_source"]["raw_string"].encode("utf-8")


def fetcher_base64_file(resource):
    return base64.b64decode(resource["body_source"]["raw_base64"])


def fetcher_url_file(resource):
    url = resource["body_source"]["url"]
    logger.info("Fetching file from %s", url)
    return urllib.request.urlopen(url).read()


FETCHERS = {
    "utf8/string": fetcher_utf8_string,
    "base64/file": fetcher_base64_file,
    "url/file": fetcher_url_file,
    # TODO "url/git", "url/tar" "hash/cache"
}


def fetch_resources(resources, on_fetched, get_from_cache=None):
    """
    on_fetched(resource, data)
    get_from_cache(hash)
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
        # TODO Catch fetch error.
        on_fetched_error = on_fetched(resource, resource_fetcher(resource))
        if on_fetched_error:
            return on_fetched_error
