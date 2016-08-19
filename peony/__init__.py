"""  peony-twitter

    An asynchronous Twitter API client for Python
"""
# -*- coding: utf-8 -*-

__author__ = "Florian Badie"
__author_email__ = "florianbadie@gmail.com"

__version__ = "0.1"

__license__ = "MIT License"

__keywords__ = "twitter, asyncio, asynchronous"

from .client import PeonyClient, BasePeonyClient
from .commands import EventStream, task, event_handler, events
