# -*- coding: utf-8 -*-
"""
===============
 peony-twitter
===============

  An asynchronous Twitter API client for Python 3.5+

"""

__author__ = "Florian Badie"
__author_email__ = "florianbadie@gmail.com"
__url__ = "https://github.com/odrling/peony-twitter"

__version__ = "1.0.0"

__license__ = "MIT License"

__keywords__ = "twitter, asyncio, asynchronous"

from .client import BasePeonyClient, PeonyClient  # noqa
from .commands import EventStream, event_handler, events, task, init_task  # noqa
