# -*- coding: utf-8 -*-

import re
from functools import wraps

import peony.utils

from . import utils


def process_keys(func):
    """
    Raise error for keys that are not strings
    and add the prefix if it is missing
    """

    @wraps(func)
    def decorated(self, k, *args):
        if not isinstance(k, str):
            msg = "%s: key must be a string" % self.__class__.__name__
            raise ValueError(msg)

        if not k.startswith(self.prefix):
            k = self.prefix + k

        return func(self, k, *args)

    return decorated


class Functions(dict):
    """
        Functions of an event handler

    When a key is found in the text given as an argument to
    :meth:`_run` the corresponding function is called.

    Parameters
    ----------
    prefix : str
        Prefix of the functions
    strict : bool
        In strict mode the command must be at the beginning of the
        string
    args
        Positional arguments passed to :func:`dict.__init__`
        for those who want to do some shady things
    kwargs
        Keyword arguments passed to :func:`dict.__init__`
    """

    def __init__(self, *args, prefix=None, strict=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = prefix
        ex = re.escape(prefix) + r"[^\s]+"
        self.prog = re.compile(ex)
        self.strict = strict

    @process_keys
    def __getitem__(self, k):
        """get the function you want"""
        return super().__getitem__(k)

    @process_keys
    def __setitem__(self, k, v):
        if self.prefix is None:
            raise RuntimeError("To add commands you must set a prefix")

        super().__setitem__(k, v)

    def __repr__(self):
        return "{classname}({super})".format(
            classname=self.__class__.__name__, super=", ".join(super().keys())
        )

    def _get(self, text):
        """
            Analyze the text to get the right function

        Parameters
        ----------
        text : str
            The text that could call a function
        """
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

    async def run(self, *args, data):
        """run the function you want"""
        cmd = self._get(data.text)

        try:
            if cmd is not None:
                command = self[cmd](*args, data=data)
                return await peony.utils.execute(command)

        except Exception:
            fmt = "Error occurred while running function {cmd}:"
            peony.utils.log_error(fmt.format(cmd=cmd))

    def __call__(self, func, name=None):
        name = name or func.__name__
        self[name] = func

        return func


class Commands(Functions):
    def __init__(self, prefix=None):
        super().__init__(prefix=prefix)

        @self
        def help(_self, data, *args, **kwargs):
            """show commands help"""
            kdoc = [
                (key, utils.doc(value))
                for key, value in self.items()
                if utils.permission_check(
                    data, command_permissions=_self.permissions, command=value
                )
            ]

            kdoc.sort(key=self._key)

            msg = ["{key}: {doc}".format(key=key, doc=doc) for key, doc in kdoc]

            return "\n".join(msg)

    def _key(self, item):
        key, __ = item
        if key == self.prefix + "help":
            return ""  # /help is the first in the message
        else:
            return key  # sort other commands alphabeticaly

    def restricted(self, *permissions):
        def decorator(func):
            @wraps(func)
            async def decorated(_self, *args, data):
                permission = utils.permission_check(
                    data, command_permissions=_self.permissions, permissions=permissions
                )

                if permission:
                    argcount = func.__code__.co_argcount - 1
                    args = (*args, data)[:argcount]
                    cmd = func(_self, *args)

                    return await peony.utils.execute(cmd)

            decorated.permissions = permissions

            return self(decorated)

        return decorator
