# -*- coding: utf-8 -*-

from functools import update_wrapper


class task:

    def __init__(self, func):
        update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        return self.__wrapped__(*args, **kwargs)
