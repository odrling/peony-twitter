# -*- coding: utf-8 -*-


from functools import update_wrapper


class Task:

    def __init__(self, func):
        self.__wrapped__ = None
        update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        return self.__wrapped__(*args, **kwargs)

    def __str__(self):
        return "<{cls} {name}()>".format(cls=self.__class__.__name__,
                                         name=self.__wrapped__.__name__)

    def __repr__(self):
        return str(self)


task = Task
