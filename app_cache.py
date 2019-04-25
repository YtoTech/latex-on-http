# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.process
    ~~~~~~~~~~~~~~~~~~~~~
    Manage Latex-On-HTTP cache process lifecycle.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging.config
import sys
import zmq
from latexonhttp.caching.bridge import serialize_message, deserialize_message
from latexonhttp.caching.resources import (
    do_forward_resource_to_cache,
    do_get_resource_from_cache,
)
from latexonhttp.caching.store import get_cache_metadata

# Logging.
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"default": {"format": "[%(levelname)s %(module)s] %(message)s"}},
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "default"}
        },
        "loggers": {"latexonhttp": {"handlers": ["console"], "level": "DEBUG"}},
    }
)

logger = logging.getLogger("latexonhttp")

context = zmq.Context()

ACTIONS_MAP = {
    "forward_resource_to_cache": {"fn": do_forward_resource_to_cache, "mode": "async"},
    "get_resource_from_cache": {"fn": do_get_resource_from_cache, "mode": "sync"},
    "get_cache_metadata": {"fn": get_cache_metadata, "mode": "sync"},
}

if __name__ == "__main__":
    logger.info("Starting Latex-On-HTTP cache process")
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:10000")
    while True:
        message = deserialize_message(socket.recv())
        logger.info(
            "Received message: %s",
            {**message, "args": {**message["args"], "data": None}},
        )
        action_desc = ACTIONS_MAP.get(message["action"])
        if not action_desc:
            logger.error("Unknow action %s", message["action"])
            raise RuntimeError("Unknow action {}".format(message["action"]))
        # Async? Reply directly.
        if action_desc["mode"] == "async":
            socket.send(b"")
        # Invoke action.
        response = action_desc["fn"](**message["args"])
        # Send response.
        if action_desc["mode"] == "sync":
            logger.debug("Send response for %s", message["action"])
            socket.send(serialize_message(response))
