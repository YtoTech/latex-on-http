# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.bridge
    ~~~~~~~~~~~~~~~~~~~~~
    Bridge to LaTeX-On-HTTP cache process.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import os
import logging
import msgpack
import zmq

REQUEST_RECV_TIMEOUT = 1500
REQUEST_RETRIES = 2

logger = logging.getLogger(__name__)

context = zmq.Context()
req_socket = None
dealer_socket = None

# Allows to disable cache if no host defined.
CACHE_HOST = os.getenv("CACHE_HOST")

# ; The caching is forwarded to a decicated process
# ; for the whole LaTeX-On-HTTP node to ensure consistency.
# ; Also will avoid cache management overhead in main process
# (with async operations).
# ; --> Uses a zeroMQ socket as the API.
# ; The cache layer could then be 100% independent.


def get_cache_process_sync_socket():
    if not CACHE_HOST:
        return None
    # Connect only one time and let open.
    # (Does this can timeout? Will see)
    # (Also mut try to re-connect on errors)
    global req_socket
    if not req_socket:
        req_socket = context.socket(zmq.REQ)
        req_socket.connect(f"tcp://{CACHE_HOST}:10000")
    return req_socket


def clore_cache_process_sync_socket(linger=0):
    global req_socket
    if req_socket:
        socket.setsockopt(zmq.LINGER, linger)
        socket.close()
        req_socket = None


def get_cache_process_async_socket():
    if not CACHE_HOST:
        return None
    # Connect only one time and let open.
    # (Does this can timeout? Will see)
    # (Also mut try to re-connect on errors)
    global dealer_socket
    if not dealer_socket:
        dealer_socket = context.socket(zmq.DEALER)
        dealer_socket.connect(f"tcp://{CACHE_HOST}:10001")
    return dealer_socket


def serialize_message(message):
    return msgpack.packb(message, use_bin_type=True)


def deserialize_message(data):
    return msgpack.unpackb(data, raw=False)


def request_cache_process_sync(
    message, timeout=REQUEST_RECV_TIMEOUT, retries=REQUEST_RETRIES
):
    # We implement a lazy pirate pattern.
    # https://zguide.zeromq.org/docs/chapter4/#Client-Side-Reliability-Lazy-Pirate-Pattern
    socket = get_cache_process_sync_socket()
    if not socket:
        return False, {"error": "No cache process host defined"}
    try:
        socket.send(serialize_message(message), zmq.NOBLOCK)
    except zmq.ZMQError as ze:
        return False, {"error": "ZMQ socket failure", "message": str(ze)}
    # Get reply.
    # Use polling to handle timeouts
    # and allow to choose timeout specific for the request.
    try:
        retries_left = retries
        while True:
            if (socket.poll(REQUEST_RECV_TIMEOUT) & zmq.POLLIN) != 0:
                response = socket.recv()
                return True, deserialize_message(response)
            retries_left = -1
            # Socket is confused. Close and remove it.
            clore_cache_process_sync_socket()
            if retries_left == 0:
                return False, {"error": "ZMQ socket timeout", "retries": retries}
            socket = get_cache_process_sync_socket()
            if not socket:
                return False, {"error": "No cache process host defined"}
            socket.send(serialize_message(message), zmq.NOBLOCK)

    except zmq.ZMQError as ze:
        return False, {"error": "ZMQ socket failure", "message": str(ze)}


def request_cache_process_async(message):
    socket = get_cache_process_async_socket()
    if not socket:
        return False, {"error": "No cache process host defined"}
    try:
        socket.send(serialize_message(message), zmq.NOBLOCK)
    except zmq.ZMQError as ze:
        return False, {"error": "ZMQ socket failure", "message": str(ze)}
    return True, None
    # We do not expect a response.
    # We could have an async mode with responses,
    # which would requires to ask for responses
    # at any time. The use would be responsible for
    # matching requests with responses (for eg. using an id).
    # This mode could be used to launch a batch of requests
    # to the cache process and then wait for all responses.
    # (instead of REQ/REP sequentially)
    # http://zguide.zeromq.org/py:asyncsrv
    # http://zguide.zeromq.org/php:chapter3#The-DEALER-to-DEALER-Combination
