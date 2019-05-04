# -*- coding: utf-8 -*-


from .event_handlers import EventHandler, EventStream, EventStreams  # noqa
from .event_types import events  # noqa
from .tasks import task  # noqa

event_handler = EventHandler.event_handler
