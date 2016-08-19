# -*- coding: utf-8 -*-


class Task:

    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)
