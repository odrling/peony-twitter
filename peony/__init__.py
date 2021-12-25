# -*- coding: utf-8 -*-
"""
===============
 peony-twitter
===============

  An asynchronous Twitter API client for Python 3.6+

"""

__author__ = "Florian Badie"
__author_email__ = "florianbadie@gmail.com"
__url__ = "https://github.com/odrling/peony-twitter"

__version__ = "2.1.0"

__license__ = "MIT License"

__keywords__ = "twitter, asyncio, asynchronous"

import logging

logger = logging.getLogger(__name__)

from .client import BasePeonyClient, PeonyClient  # noqa
from .commands import EventStream, event_handler, events, task  # noqa
from .utils import ErrorHandler, set_debug  # noqa
