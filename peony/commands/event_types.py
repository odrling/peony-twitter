# -*- coding: utf-8 -*-

from functools import wraps

from ..utils import get_args
from .event_handlers import EventHandler

on = "on_{name}"


def _get_value(func):
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
        strict : bool, optional
            If set to True the command must be at the beginning
            of the message. Defaults to False.

        Returns
        -------
        function
            a decorator that returns an :class:`EventHandler` instance
        """

        def decorated(func):
            return EventHandler(
                func=func, event=self.event, prefix=prefix, strict=strict
            )

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
        self.__doc__ = func.__doc__

    def envelope(self):
        """returns an :class:`Event` that can be used for site streams"""

        def enveloped_event(data):
            return "for_user" in data and self._func(data.get("message"))

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

    def __setitem__(self, key, func):
        event = func if isinstance(func, Event) else Event(func, key)
        super().__setitem__(key, event)

    def __getattr__(self, item):
        return self[item]

    def _set_aliases(self, *keys, event=None, func=None):
        name = func.__name__
        keys = [key if "{name}" not in key else key.format(name=name) for key in keys]

        if func:
            event = self(func)
        elif event:
            event = self.event(event)
        else:
            raise RuntimeError("Could not set alias")

        event.__doc__ += "\n:aliases: %s" % ", ".join(keys).format(name=name)

        for key in keys:
            self[key] = event
            self.aliases[key] = self[name]

        return event

    def alias(self, *keys):
        def decorator(func):
            event = self._set_aliases(*keys, func=func)

            return event

        return decorator

    def event_alias(self, *keys):
        def decorator(func):
            event = self._set_aliases(*keys, event=func)

            return event

        return decorator

    def event(self, func):
        if not len(get_args(func)):
            value = _get_value(func)

            @wraps(func)
            def decorated(data):
                return data.get("event") == value

            self[func.__name__] = decorated
            self["on_" + func.__name__] = decorated
            self[func.__name__].__doc__ = func.__doc__
            return self[func.__name__]
        else:
            self[func.__name__] = func
            return self[func.__name__]

    def __call__(self, func):
        name = func.__name__

        if not len(get_args(func)):
            value = _get_value(func)

            @wraps(func)
            def decorated(data):
                return value in data

            self[name] = decorated
        else:
            self[name] = func

        return self[name]

    @property
    def no_aliases(self):
        return {key: value for key, value in self.items() if key not in self.aliases}

    def priority(self, p):
        def decorated(func):
            func.priority = p
            return self(func)

        return decorated


events = Events()


@events
def friends(data):
    """
        Event triggered on connection to an userstream

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#friends-lists-friends
    """  # noqa: E501
    return "friends" in data or "friends_str" in data


@events.alias(on, "on_dm")
def direct_message():
    """
        Event triggered when a direct message is received

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#direct-messages
    """


@events.alias(on, "retweet", "on_retweet")
@events.priority(-1)
def retweeted_status(data):
    """
        Event triggered when the data corresponds to a retweet

    For more information:
    https://dev.twitter.com/overview/api/tweets
    """
    return tweet(data) and "retweeted_status" in data


@events.alias(on)
def tweet(data):
    """
        Event triggered when the data corresponds to a tweet
    If there is no handler for the :func:`retweeted_status` event
    then the data could correspond to a retweet

    For more information:
    https://dev.twitter.com/overview/api/tweets
    """
    return "text" in data


@events.alias(on, "deleted_tweet")
def delete():
    """
        Event triggered when an user deletes a tweet

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#status-deletion-notices-delete
    """  # noqa: E501


@events.alias("location_deleted")
def scrub_geo():
    """
        Event triggered when an user deletes their location on a range of
        tweets

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#location-deletion-notices-scrub-geo
    """  # noqa: E501


@events.event
def limit():
    """
        Event triggered when the data corresponds to a stream limit notice

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#limit-notices-limit
    """  # noqa: E501


@events.event
def status_withheld():
    """
        Event triggered upon receiving a status withheld notice

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#withheld-content-notices-status-withheld-user-withheld
    """  # noqa: E501


@events.event
def user_withheld():
    """
        Event triggered upon receiving a status withheld notice

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#user-withheld
    """


@events.alias(on)
def disconnect():
    """
        Event triggered upon receiving a disconnect notice
    Note that the disconnect message may not be received when experiencing
    network issues.

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#disconnect-messages-disconnect
    """  # noqa: E501


# warnings


@events.alias(on)
def warning():
    """
        Event triggered when receiving a warning

    For more information:

    * https://dev.twitter.com/streaming/overview/messages-types#stall-warnings-warning
    * https://dev.twitter.com/streaming/overview/messages-types#too-many-follows-warning
    """  # noqa: E501


@events.alias(on)
def stall_warning(data):
    """
        Event triggered when receiving a stall warning

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#stall-warnings-warning
    """  # noqa: E501
    return warning(data) and data.get("warning").get("code") == "FALLING_BEHIND"


@events.alias(on)
def too_many_follows(data):
    """
        Event triggered when receiving a "too many follows" warning

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#too-many-follows-warning
    """  # noqa: E501
    return warning(data) and data.get("warning").get("code") == "FOLLOWS_OVER_LIMIT"


# events, the data looks like; {"event": EVENT_NAME, ...}


@events.event
def access_revoked():
    """
        Event triggered when the user is deauthorized

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def follow():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def unfollow():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def block():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def unblock():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def favorite():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def unfavorite():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def list_created():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def list_destroyed():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def list_updated():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def list_member_added():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def list_member_removed():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def list_user_subscribed():  # noqa: E501
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def list_user_unsubscribed():  # noqa: E501
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def quoted_tweet():
    """

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#events-event
    """


@events.event
def user_update():
    """
            Event triggered when an user updates their profile

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#user_update
    """


# Site stream control messages


@events.alias("control_message")
def control():
    """
        Event triggered upon receiving a control message

    For more information:
    https://dev.twitter.com/streaming/overview/messages-types#control-messages-control
    """  # noqa: E501


# Internal peony events


@events.alias(on, "first_connection")
def connected():
    """
    event_triggered on the first connection to a stream
    """


@events.alias(on)
@events.priority(1)
def connect(data):
    """
    event triggered on connection or reconnection to a stream
    """
    return connected(data) or stream_restart(data)


@events.alias(on, "on_restart", "restart")
def stream_restart():
    """
    Event triggered on stream restart
    """


@events.alias(on, "reconnect", "on_reconnect")
def reconnecting_in():
    """
        Event triggered when a stream restart is scheduled

    the data contains the number of seconds to wait is seconds as its
    ``'reconnecting_in'`` item.
    """


# matches any event that wasn't handled
@events.priority(1024)
def default(_):
    """
    Event triggered when the data didn't trigger any handled event
    """
    return True
