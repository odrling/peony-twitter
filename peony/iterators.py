# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod


class AbstractIterator(ABC):
    """
        Asynchronous iterator

    Parameters
    ----------
    _request
        Main request
    **kwargs
        Parameters of the request
    """

    def __init__(self, _request, **kwargs):
        self.request = _request
        self.kwargs = kwargs

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
    _request :
        Main request
    _parameter : str
        Parameter to change for each request
    _force : bool
        Keep the iterator after empty responses
    kwargs:
        Request parameters
    """

    def __init__(self, _request, _parameter, _force=False, **kwargs):
        """ Keep all the arguments as class attributes """
        self.param = _parameter
        self.force = _force
        super().__init__(_request, **kwargs)

    async def __anext__(self):
        """ return each response until getting an empty data """
        response = await self.request(**self.kwargs)

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
    _request:
        Main request
    kwargs:
        Parameters of the request
    """

    def __init__(self, _request, **kwargs):
        super().__init__(_request,
                         _parameter="max_id",
                         _force=False,
                         **kwargs)

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
    _request
        Main request
    _force : bool
        Keep the iterator after empty responses
    _fill_gaps : bool
        Fill the gaps (if there are more than ``count`` tweets to get)
    **kwargs
        Parameters of the request
    """

    def __init__(self, _request, _force=True, _fill_gaps=True, **kwargs):
        super().__init__(_request,
                         _parameter="since_id",
                         _force=_force,
                         **kwargs)

        self.fill_gaps = _fill_gaps
        self.last_id = None

    async def set_param(self, response):
        if response:
            if self.fill_gaps:
                self.kwargs[self.param] = response[0]['id'] - 1
                print(self.kwargs)
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
                responses = with_max_id(
                    _request=self.request,
                    max_id=response[0]['id'] - 1,
                    **self.kwargs
                )

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
    _request
        Main request
    **kwargs
        Parameters of the request
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
