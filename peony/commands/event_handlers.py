# -*- coding: utf-8 -*-

from . import utils
from .commands import Commands
from .tasks import Task


def unpack(*args, **values):
    items = [arg for arg in args
             if isinstance(arg, (tuple, list)) and len(arg) == 2]
    extra_values = {key: value for key, value in items}

    values.update(extra_values)

    keys = [arg for arg in args if not isinstance(arg, (tuple, list))]
    keys.extend(values.keys())

    return keys, values


class EventHandler(Task):

    def __init__(self, *args, func, prefix=None, **values):
        super().__init__(func)

        self.keys, self.values = unpack(*args, **values)
        self.prefix = prefix

        if prefix is not None:
            self.command = Commands(prefix=prefix)

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
        raise RuntimeError("You must overload stream property in " + clsname)

    async def _start(self):
        async with self.stream_request as ressource:
            async for data in ressource:
                try:
                    await self._run(data)
                except Exception as e:
                    msg = "error in %s._start:" % self.__class__.__name__
                    print(msg, e)

    def _check(self, func):
        if not func.startswith("_"):
            return isinstance(getattr(self, func), EventHandler)
        else:
            return False

    @staticmethod
    def _test(data, keys, values):
        if any(key not in data for key in keys):
            return False

        for key, value in values.items():
            if isinstance(data[key], dict):
                if isinstance(value, dict):
                    value = value.items()
                elif not isinstance(value, (list, tuple, set)):
                    value = (value,)

                if self._test(data[key], *unpack(value)) is False:
                    return False
            else:
                if data[key] != val:
                    return False

        return True

    def _get(self, data):
        try:
            functions = [getattr(self, func)
                         for func in dir(self) if self._check(func)]

            for event_handler in functions:
                keys, values = event_handler.keys, event_handler.values
                if self._test(data, keys, values):
                    return event_handler

        except Exception as e:
            msg = "error in %s._get:" % self.__class__.__name__
            print(msg, e)

    async def _run(self, data):
        event_handler = self._get(data)

        try:
            if event_handler:
                coro = event_handler(self, data)
                return await utils.execute(coro)

        except Exception as e:
            fmt = "error occurred while running {classname} {handler}: {error}"
            msg = fmt.format(classname=self.__class__.__name__,
                             handler=event_handler.__name__,
                             error=e)

            print(msg)


class EventStreams(list):

    @property
    def tasks(self):
        return [stream._start() for stream in self]

    @property
    def task(self):
        if len(self) == 1:
            return self[0]._start()
        elif self:
            raise RuntimeError("more than 1 event stream")
        else:
            raise RuntimeError("no event stream")

    def setup(self, client):
        for i in range(len(self)):
            self[i] = self[i](client=client)
