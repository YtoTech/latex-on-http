# -*- coding: utf-8 -*-
"""
    tests.test_cache
    ~~~~~~~~~~~~~~~~~~~~~
    Test the LaTeX-On-HTTP file fetchers.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import pytest
import requests


def test_resource_flush_and_get_cached_files_empty(latex_on_http_api_url):
    # Flush.
    r = requests.delete(
        latex_on_http_api_url + "/caches/resources",
    )
    assert r.status_code == 204
    r = requests.get(
        latex_on_http_api_url + "/caches/resources",
    )
    assert r.status_code == 200
    response_payload = r.json()
    assert response_payload["cached_resources"] == []
    assert response_payload["total_size"] == 0


# TODO Check cached resources.
def test_resource_cache_file(latex_on_http_api_url):
    r = requests.post(
        latex_on_http_api_url + "/builds/sync",
        json={
            "resources": [
                {
                    "content": "\\documentclass{article}\n\\begin{document}\nHello World\n\\end{document}",
                    "main": True,
                },
                {
                    "url": "https://www.ytotech.com/images/ytotech_logo.png",
                    "path": "logo.png",
                },
            ],
        },
    )
    assert r.status_code == 201
    # Then we can check the cache.
    r = requests.get(
        latex_on_http_api_url + "/caches/resources",
    )
    assert r.status_code == 200
    response_payload = r.json()
    assert response_payload["cached_resources"] == [{"size": 6783}]
    assert response_payload["total_size"] == 6783
    # Check cached resources.
    r = requests.post(
        latex_on_http_api_url + "/caches/resources/check_cached",
        json={
            "resources": [
                {
                    "hash": "sha256:683d205d5044f5822c01424189a96e710512f79fe322bbcd8a83a79c8d27cf70",
                },
                {
                    "hash": "sha256:b9797e795d0c45e23671d6037fc77f81a0b4783b",
                },
            ],
        },
    )
    assert r.status_code == 200
    response_payload = r.json()
    print(response_payload)
    assert response_payload["resources"] == {
        "sha256:683d205d5044f5822c01424189a96e710512f79fe322bbcd8a83a79c8d27cf70": {
            "hit": True
        },
        "sha256:b9797e795d0c45e23671d6037fc77f81a0b4783b": {"hit": False},
    }
