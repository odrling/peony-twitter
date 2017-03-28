# -*- coding: utf-8 -*-

from functools import wraps

from .event_handlers import EventHandler
from ..utils import get_args


def get_value(func):
    value = func()

    if value is None:
        value = func.__name__

    return value

class Handler:

    def __init__(self, event):
        self.event = event

    def __call__(self, func):
        return EventHandler(func=func, event=self.event)

    def with_prefix(self, prefix):

        def decorated(func):
            return EventHandler(func=func, event=self.event, prefix=prefix)

        return decorated


class Event:

    def __init__(self, func, name):
        self._func = func
        self.handler = Handler(func)
        self.name = name

    def envelope(self):

        def enveloped_event(data):
            return 'for_user' in data and self._func(data.get('message'))

        return self.__class__(enveloped_event, self.name)

    for_user = envelope

    def __str__(self):
        return "Event {name}".format(name=self.name)

    def __repr__(self):
        return str(self)


class Events(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aliases = {}

    def __getattr__(self, key):
        return self[key]

    def __setitem__(self, key, func):
        super().__setitem__(key, Event(func, key))

    def _set_aliases(self, *keys, func):
        for key in keys:
            if "{name}" in key:
                key = key.format(name=func.__name__)

            self[key] = func
            self.aliases[key] = self[func.__name__]

    def alias(self, *keys):

        def decorator(func):
            func = self(func)
            self._set_aliases(*keys, func=func)

            return func

        return decorator

    def event_alias(self, *keys):

        def decorator(func):
            func = self.event(func)
            self._set_aliases(*keys, func=func)

            return func

        return decorator

    def event(self, func):
        if not len(get_args(func)):
            value = get_value(func)

            @wraps(func)
            def decorated(data):
                return data.get('event') == value

            self[func.__name__] = decorated
            self['on_' + func.__name__] = decorated
            return decorated
        else:
            self[func.__name__] = func
            return func

    def __call__(self, func):
        if not len(get_args(func)):
            value = get_value(func)

            @wraps(func)
            def decorated(data):
                return value in data

            self[func.__name__] = decorated
            return decorated
        else:
            self[func.__name__] = func
            return func

    @property
    def no_aliases(self):
        return {key: value for key, value in self.items()
                if key not in self.aliases}


events = Events()

on = 'on_{name}'


@events.alias('on_connect', 'connect')
def friends(data):
    return 'friends' in data or 'friends_str' in data


@events.alias(on, 'on_dm')
def direct_message():
    pass


@events.alias(on)
def tweet(data):
    return 'text' in data and not 'event' in data


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
def access_revoked():
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
