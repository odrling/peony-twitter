# -*- coding: utf-8 -*-
"""
===============
 peony-twitter
===============

  An asynchronous Twitter API client for Python 3.8+

"""

__version__ = "3.0.0"

import logging

logger = logging.getLogger(__name__)

from .client import BasePeonyClient, PeonyClient  # noqa
from .commands import EventStream, event_handler, events, task  # noqa
from .utils import ErrorHandler, set_debug  # noqa
