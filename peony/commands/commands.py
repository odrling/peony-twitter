# -*- coding: utf-8 -*-

from functools import wraps
import re
import sys

from . import utils
from ..utils import print_error


class Functions(dict):

    def __init__(self, *args, prefix=None, strict=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = prefix
        ex = re.escape(prefix) + "[^ \n\t]+"
        self.prog = re.compile(ex)
        self.strict = strict

    def __getitem__(self, k):
        if not isinstance(k, str):
            msg = "%s key must be a string" % self.__class__.__name__
            raise ValueError(msg)

        if not k.startswith(self.prefix):
            k = self.prefix + k

        return super().__getitem__(k)

    def __setitem__(self, k, v):
        if self.prefix is None:
            raise RuntimeError("To add commands you must set a prefix")

        if not isinstance(k, str):
            msg = "%s key must be a string" % self.__class__.__name__
            raise ValueError(msg)

        if not k.startswith(self.prefix):
            k = self.prefix + k

        super().__setitem__(k, v)

    def __repr__(self):
        return "{classname}({super})".format(
            classname=self.__class__.__name__,
            super=", ".join(super().keys())
        )

    def _get(self, text):
        if self.strict:
            match = self.prog.match(text)
            if match:
                cmd = match.group()
                if cmd in self:
                    return cmd
        else:
            words = self.prog.findall(text)
            for word in words:
                if word in self:
                    return word

    async def run(self, *args, data, **kwargs):
        cmd = self._get(data.text)

        try:
            if cmd is not None:
                command = self[cmd](*args, data=data, **kwargs)
                return await utils.execute(command)

        except Exception as e:
            fmt = "Error occurred while running function {cmd}:"
            print_error(fmt.format(cmd=cmd))

    def __call__(self, func, name=None):
        name = name or func.__name__
        self[name] = func

        return func


class Commands(Functions):

    def __init__(self, prefix=None):
        super().__init__(prefix=prefix)

        @self
        def help(_self, data, *args, **kwargs):
            """ show commands help """
            kdoc = [
                (key, utils.doc(value))
                for key, value in self.items()
                if utils.permission_check(data,
                                          _permissions=_self.permissions,
                                          command=value)
            ]

            kdoc.sort(key=self._key)

            msg = ["`{key}`: {doc}".format(key=key, doc=doc)
                   for key, doc in kdoc]

            return "\n".join(msg)

    def _key(self, item):
        key, __ = item
        if key == '%shelp' % self.prefix:
            return ''   # /help is the first in the message
        else:
            return key  # sort other commands alphabeticaly

    def restricted(self, *permissions):
        def decorator(func):
            @wraps(func)
            async def decorated(_self, data, *args, **kwargs):
                permission = utils.permission_check(
                    data,
                    _permissions=_self.permissions,
                    permissions=permissions
                )

                if permission:
                    cmd = func(_self, data, *args, **kwargs)

                    return await utils.execute(cmd)

            decorated.permissions = permissions

            return self(decorated)

        return decorator
