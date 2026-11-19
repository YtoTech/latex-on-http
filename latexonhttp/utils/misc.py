"""
latexonhttp.utils.misc
~~~~~~~~~~~~~~~~~~~~~
LaTeX-On-HTTP miscellaneous utils.

:copyright: (c) 2019-2022 Yoan Tournade.
:license: AGPL, see LICENSE for more details.
"""

import logging.config
import os

CURRENT_API_VERSION = "2026-11-19-3"


def configure_logging():
    """Configure the ``latexonhttp`` package logging.

    Shared by every entry point so that the log level is uniformly
    driven by the ``LOGGING_LEVEL`` environment variable (DEBUG by default).
    """
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "[%(levelname)s %(module)s] %(message)s"}
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default"}
            },
            "loggers": {
                "latexonhttp": {
                    "handlers": ["console"],
                    "level": os.getenv("LOGGING_LEVEL") or "DEBUG",
                }
            },
        }
    )


def get_api_version():
    global CURRENT_API_VERSION
    return CURRENT_API_VERSION
