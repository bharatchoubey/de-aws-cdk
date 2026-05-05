from __future__ import annotations

import logging
import os
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger configured for CDK synthesis output.

    Log level is controlled by the ``LOG_LEVEL`` environment variable
    (default: ``INFO``). Valid values: DEBUG, INFO, WARNING, ERROR.

    All loggers emit to *stderr* so they never interleave with CDK's
    CloudFormation JSON that is written to *stdout*.

    Usage::

        from logger import get_logger
        log = get_logger(__name__)
        log.info("Loading config for env=%s", env)
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)2s [%(levelname)2s] %(name)2s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.propagate = False

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_name, logging.INFO))

    return logger
