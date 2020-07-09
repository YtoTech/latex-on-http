# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.bridge
    ~~~~~~~~~~~~~~~~~~~~~
    Bridge to LaTeX-On-HTTP cache process.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import msgpack
import zmq

logger = logging.getLogger(__name__)

context = zmq.Context()
req_socket = None
dealer_socket = None


# ; The caching is forwarded to a decicated process
# ; for the whole LaTeX-On-HTTP node to ensure consistency.
# ; Also will avoid cache management overhead in main process
# (with async operations).
# ; --> Uses a zeroMQ socket as the API.
# ; The cache layer could then be 100% independent.


def get_cache_process_sync_socket():
    # Connect only one time and let open.
    # (Does this can timeout? Will see)
    global req_socket
    if not req_socket:
        req_socket = context.socket(zmq.REQ)
        req_socket.connect("tcp://cache:10000")
    return req_socket


def get_cache_process_async_socket():
    # Connect only one time and let open.
    # (Does this can timeout? Will see)
    global dealer_socket
    if not dealer_socket:
        dealer_socket = context.socket(zmq.DEALER)
        dealer_socket.connect("tcp://cache:10001")
    return dealer_socket


def serialize_message(message):
    return msgpack.packb(message, use_bin_type=True)


def deserialize_message(data):
    return msgpack.unpackb(data, raw=False)


def request_cache_process_sync(message):
    socket = get_cache_process_sync_socket()
    socket.send(serialize_message(message))
    # Get reply.
    # TODO Manage timeout and server error.
    return deserialize_message(socket.recv())


def request_cache_process_async(message):
    socket = get_cache_process_async_socket()
    socket.send(serialize_message(message))
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
