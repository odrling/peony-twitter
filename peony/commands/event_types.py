# -*- coding: utf-8 -*-


class Events(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aliases = {}

    def __getattr__(self, key):
        return self[key]

    def alias(self, *keys):
        def decorator(func):
            value = callable(func) and self.get_value(func) or func
            self(func, value)

            for key in keys:
                if "{name}" in key:
                    key = key.format(name=func.__name__)

                self[key] = value
                self.aliases[key] = self[func.__name__]

            return func

        return decorator

    def event(self, func):
        value = self.get_value(func)

        def decorated():
            return [('event', value)]

        decorated.__name__ = func.__name__
        return decorated

    @property
    def no_aliases(self):
        return {key: value for key, value in self.items()
                if key not in self.aliases}

    @staticmethod
    def get_value(func):
        value = func()

        if value is None:
            value = (func.__name__,)
        elif isinstance(value, str):
            value = (value,)

        return value

    def __call__(self, func, value=None):
        value = value or self.get_value(func)
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


@events.alias('sitestream_event')
@events
def envelope():
    def decorated(*args, **kwargs):
        return ('for_user', ('message', [*args, *kwargs.items()]))
    return
