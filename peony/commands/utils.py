# -*- coding: utf-8 -*-

import asyncio


def doc(value):
    stripped_chars = " \t"

    if hasattr(value, '__doc__'):
        doc = value.__doc__.lstrip(" \n\t")
        if "\n" in doc:
            i = doc.index("\n")
            return doc[:i].rstrip(stripped_chars)
        elif doc:
            return doc.rstrip(stripped_chars)

    return ""


async def execute(coro):
    if asyncio.iscoroutine(coro):
        return await coro
    else:
        return coro


def permission_check(data, _permissions, command=None, permissions=None):
    if permissions:
        pass
    elif command:
        if hasattr(command, 'permissions'):
            permissions = command.permissions
        else:
            return True  # true if no permission is required
    else:
        msg = "{name} must be called with command or permissions argument"
        raise RuntimeError(msg.format(name="_permission_check"))

    return any(data.sender.id in _permissions[permission]
               for permission in permissions
               if permission in _permissions)

def restart_on(exc):
    def decorator(func):
        while True:
            try:
                return func
            except exc:
                pass
            except:
                raise

    return decorator

