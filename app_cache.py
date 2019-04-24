# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.process
    ~~~~~~~~~~~~~~~~~~~~~
    Manage Latex-On-HTTP cache process lifecycle.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import sys
import zmq
from latexonhttp.caching.bridge import serialize_message, deserialize_message
from latexonhttp.caching.resources import (
    do_forward_resource_to_cache,
    do_get_resource_from_cache,
)

logger = logging.getLogger(__name__)

context = zmq.Context()

ACTIONS_MAP = {
    "forward_resource_to_cache": {"fn": do_forward_resource_to_cache, "mode": "async"},
    "get_resource_from_cache": {"fn": do_get_resource_from_cache, "mode": "sync"},
}

if __name__ == "__main__":
    print("starting")
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:10000")
    while True:
        print("RECV")
        # TODO Uses logging.
        sys.stdout.flush()
        message = deserialize_message(socket.recv())
        print({**message, "args": {**message["args"], "data": None}})
        action_desc = ACTIONS_MAP.get(message["action"])
        if not action_desc:
            logger.error("Unknow action %s", message["action"])
            raise RuntimeError("Unknow action {}".format(message["action"]))
        # Async? Reply directly.
        if action_desc["mode"] == "async":
            print("REP async")
            socket.send(b"")
            # socket.send(serialize_message("void"))
        # TODO Uses logging.
        sys.stdout.flush()
        # Invoke action.
        response = action_desc["fn"](**message["args"])
        # Send response.
        if action_desc["mode"] == "sync":
            print("REP sync")
            socket.send(serialize_message(response))
