# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.bridge
    ~~~~~~~~~~~~~~~~~~~~~
    Bridge to Latex-On-HTTP cache process.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import pickle
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


# TODO Uses https://msgpack.org/#languages as serializer?
# https://pyzmq.readthedocs.io/en/latest/serialization.html
# Currently this is not good: Python-based data API, will be hard to bridge
# to other languages.


def serialize_message(message):
    return pickle.dumps(message)


def deserialize_message(data):
    return pickle.loads(data)


def request_cache_process_sync(message):
    socket = get_cache_process_socket()
    socket.send(serialize_message(message))
    # Get reply.
    # TODO Timeout.
    return deserialize_message(socket.recv())


def request_cache_process_async(message):
    socket = get_cache_process_socket()
    socket.send(serialize_message(message))
    # Get the REP without reading it.
    socket.recv()
