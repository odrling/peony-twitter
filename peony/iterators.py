# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod


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

    async def __aiter__(self):
        return self

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
        super().__init__(request)

    async def __anext__(self):
        """ return each response until getting an empty data """
        request = self.request(**self.kwargs)
        response = await request
        if response:
            response = await self.call_on_response(response)
        elif not self.force:
            raise StopAsyncIteration

        return response

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

    async def call_on_response(self, response):
        """
            The parameter is set to the id of the tweet at index i - 1
        """
        self.kwargs[self.param] = response[-1]['id'] - 1
        return response


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

    async def set_param(self, response):
        if response:
            if self.fill_gaps:
                self.kwargs[self.param] = response[0]['id'] - 1
                self.last_id = response[0]['id']
            else:
                self.kwargs[self.param] = response[0]['id']

    async def call_on_response(self, response):
        """
        Try to fill the gaps and strip last tweet from the response
        if its id is that of the first tweet of the last response

        Parameters
        ----------
        response : dict or list
            The response
        """
        since_id = self.kwargs.get(self.param, 0) + 1

        if self.fill_gaps:
            if response[-1]['id'] != since_id:
                max_id = response[-1]['id'] - 1
                responses = with_max_id(self.request(**self.kwargs,
                                                     max_id=max_id))

                async for tweets in responses:
                    response.extend(tweets)

            if response[-1]['id'] == self.last_id:
                response = response[:-1]

                if not response and not self.force:
                    raise StopAsyncIteration

        await self.set_param(response)

        return response


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
