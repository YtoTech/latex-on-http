# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.bridge
    ~~~~~~~~~~~~~~~~~~~~~
    Bridge to Latex-On-HTTP cache process.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import json
import zmq

logger = logging.getLogger(__name__)

context = zmq.Context()


# ; TODO Actually the caching must be forwarded to a decicated process
# ; for the whole node to ensure consistency.
# ; Also will avoid cache management overhead in main process.
# ; --> Uses a zeroMQ socket as the API.
# ; The cache layer could then be 100% independent.
# ; For eg. could be implemented in Go, with a mixed
# ; in-memory and on-disk cache.
# ; There could be a memcached adapter, to rely on existing
# ; caching technology.
# ; With enough data, there could be neural-network trained
# ; to optimized bandwidth-saving cache hits.

# ; GO GO GO zeroMQ bridge.
# ; Update Docker image
# ; add zeroMQ lib;
# ; install Python wrapper;
# ; launch caching process (docker-compose);
# ; forward/bridge using REQ/RES socket.


def get_cache_process_socket():
    # TODO Connect only one time and let open?
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://cache:10000")
    # TODO Close? with statement?
    return socket


def serialize_message(message):
    return json.dumps(message)


def deserialize_message(data):
    return json.loads(data)


def request_cache_process_sync(message):
    socket = get_cache_process_socket()
    socket.send(serialize_message(message))
    # Get reply.
    return deserialize_message(socket.recv())


def request_cache_process_async(message):
    socket = get_cache_process_socket()
    socket.send(serialize_message(message))
