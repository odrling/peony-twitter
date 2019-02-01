# -*- coding: utf-8 -*-

import asyncio
import sys
from abc import ABC, abstractmethod

from .exceptions import NoDataFound


class AbstractIterator(ABC):
    """
        Asynchronous iterator

    Parameters
    ----------
    request : .requests.Request
        Main request
    """

    def __init__(self, request):
        self.request = request
        self.kwargs = request.kwargs.copy()

    def __aiter__(self):
        return self

    if sys.version_info < (3, 5, 2):  # pragma: no cover
        __aiter__ = asyncio.coroutine(__aiter__)

    @abstractmethod
    async def __anext__(self):
        """ the function called on each iteration """


class IdIterator(AbstractIterator):
    """
        Iterate using ids

    It is the parent class of MaxIdIterator and SinceIdIterator

    Parameters
    ----------
    request : .requests.Request
        Main request
    parameter : str
        Parameter to change for each request
    force : bool
        Keep the iterator after empty responses
    """

    def __init__(self, request, parameter, force=False):
        """ Keep all the arguments as class attributes """
        self.param = parameter
        self.force = force
        self._response_key = None
        self._response_list = False
        super().__init__(request)

    async def __anext__(self):
        """ return each response until getting an empty data """
        request = self.request(**self.kwargs)
        response = await request
        data = self.get_data(response)

        if data:
            await self.call_on_response(data)
        elif not self.force:
            raise StopAsyncIteration

        return response

    def get_data(self, response):
        """ Get the data from the response """
        if self._response_list:
            return response
        elif self._response_key is None:
            if hasattr(response, "items"):
                for key, data in response.items():
                    if (hasattr(data, "__getitem__")
                            and not hasattr(data, "items")
                            and len(data) > 0
                            and 'id' in data[0]):
                        self._response_key = key
                        return data
            else:
                self._response_list = True
                return response
        else:
            return response[self._response_key]

        raise NoDataFound(response=response, url=self.request.get_url())

    @abstractmethod
    async def call_on_response(self, response):
        """ function that prepares for the next request """


class MaxIdIterator(IdIterator):
    """
        Iterator for endpoints using max_id

    Parameters
    ----------
    request : .requests.Request
        Main request
    """

    def __init__(self, request):
        super().__init__(request,
                         parameter="max_id",
                         force=False)

    async def call_on_response(self, data):
        """
            The parameter is set to the id of the tweet at index i - 1
        """
        self.kwargs[self.param] = data[-1]['id'] - 1


class SinceIdIterator(IdIterator):
    """
        Iterator for endpoints using since_id

    Parameters
    ----------
    request : .requests.Request
        Main request
    force : bool
        Keep the iterator after empty responses
    fill_gaps : bool
        Fill the gaps (if there are more than ``count`` tweets to get)
    """

    def __init__(self, request, force=True, fill_gaps=False):
        super().__init__(request,
                         parameter="since_id",
                         force=force)

        self.fill_gaps = fill_gaps
        self.last_id = None

    async def set_param(self, data):
        if data:
            if self.fill_gaps:
                self.kwargs[self.param] = data[0]['id'] - 1
                self.last_id = data[0]['id']
            else:
                self.kwargs[self.param] = data[0]['id']

    async def call_on_response(self, data):
        """
        Try to fill the gaps and strip last tweet from the response
        if its id is that of the first tweet of the last response

        Parameters
        ----------
        data : list
            The response data
        """
        since_id = self.kwargs.get(self.param, 0) + 1

        if self.fill_gaps:
            if data[-1]['id'] != since_id:
                max_id = data[-1]['id'] - 1
                responses = with_max_id(self.request(**self.kwargs,
                                                     max_id=max_id))

                async for tweets in responses:
                    data.extend(tweets)

            if data[-1]['id'] == self.last_id:
                data = data[:-1]

        if not data and not self.force:
            raise StopAsyncIteration

        await self.set_param(data)


class CursorIterator(AbstractIterator):
    """
        Iterate using a cursor

    Parameters
    ----------
    request : .requests.Request
        Main request
    """

    async def __anext__(self):
        """ return each response until getting 0 as next cursor """
        if self.kwargs.get('cursor', -1) != 0:
            response = await self.request(**self.kwargs)
            self.kwargs['cursor'] = response['next_cursor']
            return response
        else:
            raise StopAsyncIteration


with_max_id = MaxIdIterator
with_since_id = SinceIdIterator
with_cursor = CursorIterator
