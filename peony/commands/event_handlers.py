# -*- coding: utf-8 -*-
import peony.utils
from . import utils
from .commands import Commands
from .tasks import task


class EventHandler(task):

    def __init__(self, func, event, prefix=None, strict=False):
        super().__init__(func)

        self.prefix = prefix
        self.is_event = event

        if prefix is not None:
            self.command = Commands(prefix=prefix, strict=strict)

    def __call__(self, *args):
        argcount = self.__wrapped__.__code__.co_argcount

        if hasattr(self, 'command'):
            args = (*args, self.command,)

        args = args[:argcount]
        return super().__call__(*args)

    def __repr__(self):
        return "<{clsname}: event:{event} prefix:{prefix}>".format(
            clsname=self.__class__.__name__,
            prefix=self.prefix,
            event=self.is_event
        )

    @classmethod
    def event_handler(cls, event, prefix=None, **values):

        def decorator(func):
            event_handler = cls(
                func=func,
                event=event,
                prefix=prefix,
                **values
            )

            return event_handler

        return decorator


class EventStream:

    def __init__(self, client):
        self._client = client
        self.functions = [getattr(self, func)
                          for func in dir(self) if self._check(func)]

        self.functions.sort(key=lambda i: getattr(i.is_event, 'priority', 0))

    def __getitem__(self, key):
        return self._client[key]

    def __getattr__(self, key):
        return getattr(self._client, key)

    @property
    def stream_request(self):
        clsname = self.__class__.__name__
        msg = "You must overload stream_request property in " + clsname
        raise RuntimeError(msg)

    @utils.restart_on(Exception)
    async def start(self):
        if callable(self.stream_request):
            stream_request = self.stream_request()
        else:
            stream_request = self.stream_request

        async with stream_request as resource:
            async for data in resource:
                try:
                    await self._run(data)
                except Exception as e:
                    msg = "error in %s._start:\n" % self.__class__.__name__
                    peony.utils.print_error(msg)

    def _check(self, func):
        if not func.startswith("_"):
            return isinstance(getattr(self, func), EventHandler)
        else:
            return False

    def _get(self, data):
        for event_handler in self.functions:
            if event_handler.is_event(data):
                return event_handler

    async def _run(self, data):
        event_handler = self._get(data)

        if event_handler:
            coro = event_handler(self, data)
            try:
                return await peony.utils.execute(coro)
            except:
                fmt = "error occurred while running {classname}.{handler}:"
                msg = fmt.format(classname=self.__class__.__name__,
                                 handler=event_handler.__name__)

                peony.utils.print_error(msg)


def check_setup(func):
    def decorated(self, client):
        if not self.is_setup:
            self.setup(client)

        return func(self, client)

    return decorated


class EventStreams(list):

    def __init__(self):
        super().__init__()
        self.is_setup = False

    @check_setup
    def get_tasks(self, client):
        return [client.loop.create_task(stream.start()) for stream in self]

    @check_setup
    def get_task(self, client):
        if len(self) == 1:
            return client.loop.create_task(self[0].start())
        elif self:
            raise RuntimeError("more than 1 event stream")
        else:
            raise RuntimeError("no event stream")

    def setup(self, client):
        for i in range(len(self)):
            self[i] = self[i](client=client)

        self.is_setup = True
