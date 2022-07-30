# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.process
    ~~~~~~~~~~~~~~~~~~~~~
    Manage LaTeX-On-HTTP cache process lifecycle.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import os
import sentry_sdk
import sentry_sdk.integrations.flask
import logging.config
import sys
import zmq
from latexonhttp.caching.bridge import serialize_message, deserialize_message
from latexonhttp.caching.resources import (
    do_forward_resource_to_cache,
    do_get_resource_from_cache,
    do_are_resources_in_cache,
    do_reset_cache,
)
from latexonhttp.caching.store import get_cache_metadata
from latexonhttp.utils.misc import get_api_version

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

if os.environ.get("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        integrations=[sentry_sdk.integrations.flask.FlaskIntegration()],
        # By default the SDK will try to use the SENTRY_RELEASE
        # environment variable, or infer a git commit
        # SHA as release, however you may want to set
        # something more human-readable.
        release=get_api_version(),
    )

logger = logging.getLogger("latexonhttp")

context = zmq.Context()

ACTIONS_MAP = {
    "forward_resource_to_cache": {"fn": do_forward_resource_to_cache, "mode": "async"},
    "get_resource_from_cache": {"fn": do_get_resource_from_cache, "mode": "sync"},
    "get_cache_metadata": {"fn": get_cache_metadata, "mode": "sync"},
    "are_resources_in_cache": {"fn": do_are_resources_in_cache, "mode": "sync"},
    "reset_cache": {"fn": do_reset_cache, "mode": "sync"},
}

# Other implementation ideas:
# ; Could be implemented in Go, with a mixed
# ; in-memory and on-disk cache.
# ; There could be a memcached adapter, to rely on existing
# ; caching technology.
# ; With enough data, there could be neural-network trained
# ; to optimized bandwidth-saving cache hits.


if __name__ == "__main__":
    logger.info("Starting LaTeX-On-HTTP cache process")
    # Initializing cache metadata.
    logger.info("Preparing cache...")
    # Reset cache.
    # (Flush cache on disk and init metadata).
    do_reset_cache()
    logger.info("Cache init process, done...")
    rep_socket = context.socket(zmq.REP)
    rep_socket.bind("tcp://*:10000")
    dealer_socket = context.socket(zmq.DEALER)
    dealer_socket.bind("tcp://*:10001")
    poller = zmq.Poller()
    poller.register(rep_socket, zmq.POLLIN)
    poller.register(dealer_socket, zmq.POLLIN)
    while True:
        # Wait for any message on both sockets.
        sockets = dict(poller.poll())
        # REP in priority, so async can't starve sync.
        # We don't mind if we wait to update the cache from latest data,
        # but we certainly want to respond as fast as possible for cache requests
        # (where the client is waiting).
        socket = rep_socket if rep_socket in sockets else next(iter(sockets.keys()))
        is_rep_socket = socket == rep_socket
        message = deserialize_message(socket.recv())
        logger.info(
            "Received message: %s",
            {**message, "args": {**message["args"], "data": None}},
        )
        action_desc = ACTIONS_MAP.get(message["action"])
        if not action_desc:
            logger.error("Unknow action %s", message["action"])
            raise RuntimeError("Unknow action {}".format(message["action"]))
        # We send no reply to DEALER sockets,
        # which is used so the clients do not block:
        # we do not want to wait for data forwarded to cache,
        # that can fail silently from time to time without being an issue.
        # http://zguide.zeromq.org/php:chapter3#The-Asynchronous-Client-Server-Pattern
        if is_rep_socket and action_desc["mode"] == "async":
            # Async: reply directly to free the client asap.
            # (This should not be used for now, we could remove sync/async altogether
            # and just use is_rep_socket as switch).
            socket.send(b"")
        # Invoke action.
        response = action_desc["fn"](**message["args"])
        if is_rep_socket and action_desc["mode"] == "sync":
            # Send response.
            logger.debug("Send response for %s", message["action"])
            socket.send(serialize_message(response))
