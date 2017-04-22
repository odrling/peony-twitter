# -*- coding: utf-8 -*-

from functools import wraps

from ..utils import get_args
from .event_handlers import EventHandler


def get_value(func):
    value = func()

    if value is None:
        value = func.__name__

    return value


class Handler:
    """
        A decorator, the decorated function is used when the
        event is detected related to this handler is detected

    Parameters
    ----------
    event : func
        a function that returns True when the data received
        corresponds to an event
    """

    def __init__(self, event):
        self.event = event

    def __call__(self, func):
        return EventHandler(func=func, event=self.event)

    def with_prefix(self, prefix, strict=False):
        """
            decorator to handle commands with prefixes

        Parameters
        ----------
        prefix : str
            the prefix of the command
        strict : :obj:`bool`, optional
            If set to True the command must be at the beginning
            of the message. Defaults to False.

        Returns
        -------
        function
            a decorator that returns an :class:`EventHandler` instance
        """

        def decorated(func):
            return EventHandler(func=func, event=self.event,
                                prefix=prefix, strict=strict)

        return decorated


class Event:
    """
        Represents an event, the handler attribute is
        an instance of Handler

    Parameters
    ----------
    func : callable
        a function that returns True when the data received
        corresponds to an event
    name : str
        name given to the event
    """

    def __init__(self, func, name):
        self._func = func
        self.handler = Handler(func)
        self.__name__ = name

    def envelope(self):
        """ returns an :class:`Event` that can be used for site streams """

        def enveloped_event(data):
            return 'for_user' in data and self._func(data.get('message'))

        return self.__class__(enveloped_event, self.__name__)

    for_user = envelope

    def __call__(self, data):
        return self._func(data)

    def __str__(self):
        return "Event {name}".format(name=self.__name__)

    def __repr__(self):
        return str(self)


class Events(dict):
    """
        A class to manage event handlers easily
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aliases = {}

    def __getattr__(self, key):
        return self[key]

    def __setitem__(self, key, func):
        event = func if isinstance(func, Event) else Event(func, key)
        super().__setitem__(key, event)

    def _set_aliases(self, *keys, func):
        for key in keys:
            if "{name}" in key:
                key = key.format(name=func.__name__)

            self[key] = func
            self.aliases[key] = self[func.__name__]

    def alias(self, *keys):

        def decorator(func):
            event = self(func)
            self._set_aliases(*keys, func=event._func)

            return event

        return decorator

    def event_alias(self, *keys):

        def decorator(func):
            event = self.event(func)
            self._set_aliases(*keys, func=event._func)

            return event

        return decorator

    def event(self, func):
        if not len(get_args(func)):
            value = get_value(func)

            @wraps(func)
            def decorated(data):
                return data.get('event') == value

            self[func.__name__] = decorated
            self['on_' + func.__name__] = decorated
            return self[func.__name__]
        else:
            self[func.__name__] = func
            return self[func.__name__]

    def __call__(self, func):
        if not len(get_args(func)):
            value = get_value(func)

            @wraps(func)
            def decorated(data):
                return value in data

            self[func.__name__] = decorated
            return self[func.__name__]
        else:
            self[func.__name__] = func
            return self[func.__name__]

    @property
    def no_aliases(self):
        return {key: value for key, value in self.items()
                if key not in self.aliases}

    def priority(self, p):

        def decorated(func):
            func.priority = p
            return self(func)

        return decorated


events = Events()

on = 'on_{name}'


@events.alias('on_connect', 'connect')
def friends(data):
    return 'friends' in data or 'friends_str' in data


@events.alias(on, 'on_dm')
def direct_message():
    pass


@events.alias(on)
@events.priority(-1024)
def retweeted_status(data):
    return tweet(data) and 'retweeted_status' in data


@events.alias(on)
def tweet(data):
    return 'text' in data and 'event' not in data


@events.alias(on, 'deleted_tweet')
def delete():
    pass


@events.alias('location_deleted')
def scrub_geo():
    pass


@events.event
def limit():
    pass


@events.event
def status_withheld():
    pass


@events.event
def user_withheld():
    pass


@events.alias(on)
def disconnect():
    pass


# warnings

@events.alias(on)
def warning():
    pass


@events.alias(on)
def stall_warning(data):
    return (warning(data) and
            data.get('warning').get('code') == "FALLING_BEHIND")


@events.alias(on)
def too_many_follows(data):
    return (warning(data) and
            data.get('warning').get('code') == "FOLLOWS_OVER_LIMIT")

# events, the data looks like; {"event": EVENT_NAME, ...}


@events.event
def access_revoked():
    pass


@events.event
def follow():
    pass


@events.event
def unfollow():
    pass


@events.event
def block():
    pass


@events.event
def unblock():
    pass


@events.event
def favorite():
    pass


@events.event
def unfavorite():
    pass


@events.event
def list_created():
    pass


@events.event
def list_destroyed():
    pass


@events.event
def list_updated():
    pass


@events.event
def list_member_added():
    pass


@events.event
def list_member_removed():
    pass


@events.event
def list_user_subscribed():
    pass


@events.event
def list_user_unsubscribed():
    pass


@events.event
def quoted_tweet():
    pass


@events.event
def user_update():
    pass


# Site stream control messages

@events.alias('control_message')
def control():
    pass


# Internal peony events

@events.alias(on, 'on_restart', 'restart')
def stream_restart():
    pass


@events.alias(on, 'reconnect', 'on_reconnect')
def reconnecting_in():
    pass


# matches any event that wasn't handled
@events.priority(1024)
def default(_):
    return True
