"""  peony-twitter

    An asynchronous Twitter API client for Python
"""

__author__ = "Florian Badie"
__author_email__ = "florianbadie@gmail.com"

__version__ = "0.1"

__license__ = "MIT License"

__keywords__ = "twitter, asyncio, asynchronous"

from .client import PeonyClient
from .commands import EventStream, task, event_handler, events
