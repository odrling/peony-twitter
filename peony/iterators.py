# -*- coding: utf-8 -*-


class IdIterator:
    """
        Iterate using ids

    It manages both max_id and since_id iterators thanks to some
    twisted logics
    """

    def __init__(self, _request, _parameter, _i, *args, **kwargs):
        """ Keep all the arguments as class attributes """
        self.request = _request
        self.kwargs = kwargs
        self.param = _parameter
        self.args = args
        self.i = _i

    def __aiter__(self):
        return self

    async def __anext__(self):
        """ return each response until getting an empty response """
        response = await self.request(*self.args, **self.kwargs)

        if response:
            i = self.i
            self.kwargs[self.param] = response[i].id + i
        else:
            raise StopAsyncIteration

        return response


class CursorIterator:
    """ Iterate using a cursor """

    def __init__(self, _request, *args, **kwargs):
        """
            Keep the arguments as class attributes and initialize
            the cursor
        """
        self.request = _request
        self.args = args

        if 'cursor' not in kwargs:
            kwargs['cursor'] = -1

        self.kwargs = kwargs

    def __aiter__(self):
        return self

    async def __anext__(self):
        """ return each response until getting 0 as next cursor """
        if self.kwargs['cursor'] != 0:
            response = await self.request(*self.args, **self.kwargs)

            self.kwargs['cursor'] = response.next_cursor

            return response
        else:
            raise StopAsyncIteration


def with_max_id(_request, *args, **kwargs):
    """ create an iterator using the max_id parameter """
    return IdIterator(_request, _parameter="max_id", _i=-1, *args, **kwargs)


def with_since_id(_request, *args, **kwargs):
    """ create an iterator using the since_id parameter """
    return IdIterator(_request, _parameter="since_id", _i=0, *args, **kwargs)


def with_cursor(_request, *args, **kwargs):
    """ create an iterator using the cursor parameter """
    return CursorIterator(_request, *args, **kwargs)
