# -*- coding: utf-8 -*-

from . import utils, Commands
from .tasks import task
from ..utils import print_error


def unpack(*args, **values):
    items = [arg for arg in args
             if isinstance(arg, (tuple, list)) and len(arg) == 2]
    extra_values = {key: value for key, value in items}

    values.update(extra_values)

    keys = [arg for arg in args if not isinstance(arg, (tuple, list))]
    keys.extend(values.keys())

    return keys, values


class EventHandler(task):

    def __init__(self, *args, func, prefix=None, **values):
        super().__init__(func)

        self.keys, self.values = unpack(*args, **values)
        self.prefix = prefix

        if prefix is not None:
            self.command = Commands(prefix=prefix)

    def __call__(self, *args, **kwargs):
        if hasattr(self, "command"):
            return super().__call__(*args, self.command, **kwargs)
        else:
            return super().__call__(*args, **kwargs)

    def __repr__(self):
        return "<{clsname}: keys:{keys} prefix:{prefix}>".format(
            clsname=self.__class__.__name__,
            prefix=self.prefix,
            keys=", ".join(self.keys)
        )


def event_handler(*args, prefix=None, **values):
    def decorator(func):
        event_handler = EventHandler(
            *args,
            func=func,
            prefix=prefix,
            **values
        )

        return event_handler

    return decorator


def _test(data, keys, values):
    if any(key not in data for key in keys):
        return False

    for key, value in values.items():
        if isinstance(data[key], dict):
            if isinstance(value, dict):
                value = value.items()
            elif not isinstance(value, (list, tuple, set)):
                value = (value,)

            if _test(data[key], *unpack(value)) is False:
                return False
        else:
            if data[key] != value:
                return False

    return True


class EventStream:

    def __init__(self, client):
        self._client = client

    def __getitem__(self, key):
        return self._client[key]

    def __getattr__(self, key):
        return getattr(self._client, key)

    @property
    def stream_request(self):
        clsname = self.__class__.__name__
        msg = "You must overload stream_request property in " + clsname
        raise RuntimeError(msg)

    @utils.restart_on(TimeoutError)
    async def _start(self):
        if callable(self.stream_request):
            stream_request = self.stream_request()
        else:
            stream_request = self.stream_request

        async with stream_request as ressource:
            async for data in ressource:
                try:
                    await self._run(data)
                except Exception as e:
                    msg = "error in %s._start:\n" % self.__class__.__name__
                    print_error(msg)

    def _check(self, func):
        if not func.startswith("_"):
            return isinstance(getattr(self, func), EventHandler)
        else:
            return False

    def _get(self, data):
        try:
            functions = [getattr(self, func)
                         for func in dir(self) if self._check(func)]

            for event_handler in functions:
                keys, values = event_handler.keys, event_handler.values
                if _test(data, keys, values):
                    return event_handler

        except:
            msg = "error in %s._get:\n" % self.__class__.__name__
            print_error(msg)

    async def _run(self, data):
        event_handler = self._get(data)

        try:
            if event_handler:
                coro = event_handler(self, data)
                return await utils.execute(coro)

        except Exception as e:
            fmt = "error occurred while running {classname} {handler}:\n"
            msg = fmt.format(classname=self.__class__.__name__,
                             handler=event_handler.__name__)

            print_error(msg)


class EventStreams(list):

    def __init__(self):
        super().__init__()
        self.is_setup = False

    def check_setup(func):
        def decorated(self, client):
            if not self.is_setup:
                self.setup(client)

            return func(self)

        return decorated

    @check_setup
    def get_tasks(self):
        return [stream._start() for stream in self]

    @check_setup
    def get_task(self):
        if len(self) == 1:
            return self[0]._start()
        elif self:
            raise RuntimeError("more than 1 event stream")
        else:
            raise RuntimeError("no event stream")

    def setup(self, client):
        for i in range(len(self)):
            self[i] = self[i](client=client)

        self.is_setup = True
