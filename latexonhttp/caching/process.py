# -*- coding: utf-8 -*-
"""
    latexonhttp.caching.process
    ~~~~~~~~~~~~~~~~~~~~~
    Manage Latex-On-HTTP cache process lifecycle.

    :copyright: (c) 2019 Yoan Tournade.
    :license: AGPL, see LICENSE for more details.
"""
import logging
import zmq

logger = logging.getLogger(__name__)

context = zmq.Context()

if __name__ == "__main__":
    print("starting")
    socket = context.socket(zmq.REP)
    socket.bind("tcp://127.0.0.1:10000")
    while True:
        message = socket.recv()
        print(message)
        # TODO Uses https://msgpack.org/#languages as serializer?
