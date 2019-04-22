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

# ; # TODO Extract the filesystem management in a module:
# ; # - determine of fs/files actions to get to construct the filesystem;
# ; # - support content/string, base64/file, url/file, url/git, url/tar, post-data/tar
# ; # - hash and make a (deterministic) signature of files uploaded;
# ; # - from the list of actions, prepare the file system (giving only a root directory);
# ; # (- add a cache management on the file system preparation subpart).


def fetcher_utf8_string(resource):
    # TODO Decode useful? .decode("utf-8")
    return resource["body-source"]["raw-string"]


def fetcher_base64_file(resource):
    return base64.b64decode(resource["body-source"]["raw-base64"])


def fetcher_url_file(resource):
    return urllib.request.urlopen(resource["body-source"]["url"]).read()


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
    for resource in resources:
        resource_fetcher = FETCHERS.get(resource["type"])
        if not resource_fetcher:
            return {"error": "FETCH_METHOD_NOT_SUPPORTED", "method": resource["type"]}
        # TODO Catch fetch error.
        on_fetched(resource, resource_fetcher(resource))
