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

RECV_TIMEOUT = 1500

logger = logging.getLogger(__name__)

context = zmq.Context()
context.setsockopt(zmq.SocketOption.RCVTIMEO, RECV_TIMEOUT)
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


def request_cache_process_sync(message):
    socket = get_cache_process_sync_socket()
    if not socket:
        return False, {"error": "No cache process host defined"}
    try:
        socket.send(serialize_message(message), zmq.NOBLOCK)
    except zmq.ZMQError as ze:
        return False, {"error": "ZMQ socket failure", "message": str(ze)}
    # Get reply.
    # TODO Use polling to handle timeouts
    # and allow to choose timeout specific for the request.
    # https://stackoverflow.com/questions/7538988/zeromq-how-to-prevent-infinite-wait
    try:
        response = socket.recv()
        return True, deserialize_message(response)
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
