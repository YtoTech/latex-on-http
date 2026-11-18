# -*- coding: utf-8 -*-
"""
tests.test_cache_decisions
~~~~~~~~~~~~~~~~~~~~~~~~~~
Check cache eviction decisions.

:copyright: (c) 2026 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

from latexonhttp.caching.resources import (
    free_space_from_first_rec,
    free_space_from_old_entries,
)


def cached_resource(name, size, added_at):
    return {"hash": name, "size": size, "added_at": added_at}


def test_cache_eviction_removes_first_entry_when_space_is_needed():
    oldest = cached_resource("oldest", 7581, "2026-11-18T02:15:37.730755")
    newest = cached_resource("newest", 6885, "2026-11-18T02:15:42.921302")

    actions = free_space_from_first_rec([oldest, newest], 4, [])

    assert actions == [{"name": "remove_resource", "resource": oldest}]


def test_cache_eviction_removes_entries_until_enough_space_is_freed():
    resources = [
        cached_resource("first", 10, "2026-11-18T02:15:37"),
        cached_resource("second", 20, "2026-11-18T02:15:38"),
        cached_resource("third", 30, "2026-11-18T02:15:39"),
    ]

    actions = free_space_from_first_rec(resources, 25, [])

    assert actions == [
        {"name": "remove_resource", "resource": resources[0]},
        {"name": "remove_resource", "resource": resources[1]},
    ]


def test_cache_eviction_uses_creation_order_not_dictionary_order():
    oldest = cached_resource("oldest", 10, "2026-11-18T02:15:37")
    newest = cached_resource("newest", 20, "2026-11-18T02:15:38")
    cache_metadata = {
        "cached_resources": {
            newest["hash"]: newest,
            oldest["hash"]: oldest,
        }
    }

    actions = free_space_from_old_entries(cache_metadata, 1)

    assert actions == [{"name": "remove_resource", "resource": oldest}]


def test_cache_eviction_is_a_no_op_when_there_is_enough_space():
    resource = cached_resource("cached", 10, "2026-11-18T02:15:37")

    assert free_space_from_first_rec([resource], 0, []) == []
    assert (
        free_space_from_old_entries({"cached_resources": {"cached": resource}}, 0) == []
    )
