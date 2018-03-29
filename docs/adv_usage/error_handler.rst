=================================
 Handle errors for every request
=================================


By default :class:`peony.exceptions.RateLimitExceeded` is handled by sleeping until
the rate limit resets and the requests are resent on :class:`asyncio.TimeoutError`.
If you would handle these exceptions differently or want to handle other
exceptions you can use the ``error_handler`` argument of
:class:`~peony.client.PeonyClient`.

.. code-block:: python

    import asyncio
    import async_timeout
    import sys

    import aiohttp
    from peony import PeonyClient, ErrorHandler

    # client using application-only authentication
    backup_client = PeonyClient(**creds, auth=peony.oauth.OAuth2Headers)

    class MyErrorHandler(ErrorHandler):
        """
            try to use backup_client during rate limits
            retry requests three times before giving up
        """

        def __init__(self, request):
            # this will set the request as self.request (REQUIRED)
            super().__init__(request)
            self.tries = 0

        @ErrorHandler.handle(exceptions.RateLimitExceeded)
        async def handle_rate_limits(self):
            """ Retry the request with another client on RateLimitExceeded """
            self.request.client = backup_client
            return ErrorHandler.RETRY

        # You can handle several requests with a single method
        @ErrorHandler.handle(asyncio.TimeoutError, TimeoutError)
        async def handle_timeout_error(self):
            """ retry the request on TimeoutError """
            return ErrorHandler.RETRY

        @ErrorHandler.handle(Exception)
        async def default_handler(self, exception):
            """ retry on other """
            print("exception: %s" % exception)

            self.tries -= 1
            if self.tries > 0:
                return ErrorHandler.RETRY
            else:
                return ErrorHandler.RAISE

        # NOTE: client.api.statuses.home_timeline.get(_tries=5) should try
        # the request 5 times instead of 3
        async def __call__(self, tries=3, **kwargs):
            self.tries = tries
            await return super().__call__(**kwargs)


    client = PeonyClient(**creds, error_handler=MyErrorHandler)


Your error handler must inherit from :class:`~peony.utils.ErrorHandler`
For every exception that you want you want to handle you should create
a method decorated by :func:`~peony.utils.ErrorHandler.handle`.
This method can return :obj:`utils.ErrorHandler.RETRY` if you want another
request to be made. By default a function with no return statement will raise
the exception, but you can explicitly raise the exception by returning
:obj:`utils.ErrorHandler.RAISE`.

.. note::
    You can also choose to not use an error handler and disable the default one
    by setting the ``error_handler`` argument to ``None``.
    If you want to disable the global error handling for a specific request
    pass a ``_error_handling`` argument to this request with a value of
    ``False``.
