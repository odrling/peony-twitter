# -*- coding: utf-8 -*-

from functools import wraps, update_wrapper

from .event_handlers import EventHandler


def get_value(func):
    value = func()

    if value is None:
        value = (func.__name__,)
    elif isinstance(value, str):
        value = (value,)

    return value


class Handler:

    def __init__(self, value):
        self.value = value

    def __call__(self, func, *args, **kwargs):
        return EventHandler(*self.value, *args, func=func, **kwargs)

    def with_prefix(self, prefix):

        def decorated(func):
            return self(func, prefix=prefix)

        return decorated


class Event(list):

    def __init__(self, value):
        super().__init__(value)
        self.handler = Handler(value)


class Events(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aliases = {}

    def __getattr__(self, key):
        return self[key]

    def __setitem__(self, key, value):
        super().__setitem__(key, Event(value))

    def alias(self, *keys):

        def decorator(func):
            value = get_value(func) if callable(func) else func
            self(func, value)

            for key in keys:
                if "{name}" in key:
                    key = key.format(name=func.__name__)

                self[key] = value
                self.aliases[key] = self[func.__name__]

            return func

        return decorator

    def event(self, func):
        value = get_value(func)

        @wraps(func)
        def decorated():
            return [('event', value)]

        return decorated

    @property
    def no_aliases(self):
        return {key: value for key, value in self.items()
                if key not in self.aliases}

    def __call__(self, func, value=None):
        value = value or get_value(func)
        self[func.__name__] = value

        return func

events = Events()

on = 'on_{name}'


@events.alias('on_connect', 'connect')
def friends():
    pass


@events.alias('on_dm', on)
def direct_message():
    pass


@events.alias(on)
def tweet():
    return 'text'


@events.alias(on, 'deleted_tweet')
def delete():
    pass


@events.alias('location_deleted')
def scrub_geo():
    pass


@events
def limit():
    pass


@events
def status_withheld():
    pass


@events
def user_withheld():
    pass


@events.alias(on)
def disconnect():
    pass


@events.alias(on, 'stall_warning')
def warning():
    pass


@events.alias(on)
@events.event
def user_update():
    pass


@events.alias(on)
@events.event
def follow():
    pass


@events.alias(on)
@events.event
def unfollow():
    pass


@events.alias(on)
def access_revoked():
    pass


@events.alias(on)
@events.event
def block():
    pass


@events.alias(on)
@events.event
def unblock():
    pass


@events.alias(on)
@events.event
def favorite():
    pass


@events.alias(on)
@events.event
def unfavorite():
    pass


@events.alias(on)
@events.event
def list_created():
    pass


@events.alias(on)
@events.event
def list_destroyed():
    pass


@events.alias(on)
@events.event
def list_updated():
    pass


@events.alias(on)
@events.event
def list_member_added():
    pass


@events.alias(on)
@events.event
def list_member_removed():
    pass


@events.alias(on)
@events.event
def list_user_subscribed():
    pass


@events.alias(on)
@events.event
def list_user_unsubscribed():
    pass


@events.alias(on)
@events.event
def quoted_tweet():
    pass


@events.alias('control_message')
@events
def control():
    pass


@events.alias(on, 'on_restart', 'restart')
@events
def stream_restart():
    pass


@events.alias(on, 'reconnect', 'on_reconnect')
@events
def reconnecting_in():
    pass


@events.alias('sitestream_event')
@events
def envelope():
    def decorated(*args, **kwargs):
        return ('for_user', ('message', [*args, *kwargs.items()]))
    return
