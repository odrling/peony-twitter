=================================
 Handle errors for every request
=================================


By default :class:`peony.exceptions.RateLimitExceeded` is handled by sleeping until
the rate limit resets and the requests are resent on :class:`asyncio.TimeoutError`.
If you would handle these exceptions another way or want to handle other
exceptions differently you can use the ``error_handler`` argument of
PeonyClient.

.. code-block:: python

    import asyncio
    import sys

    import aiohttp
    from peony import PeonyClient

    # client using application-only authentication
    backup_client = PeonyClient(**creds, auth=peony.oauth.OAuth2Headers)

    def error_handler(request):
        """
            try to use backup_client during rate limits
            retry requests three times before giving up
        """

        # NOTE: client.api.statuses.home_timeline.get(_tries=5) should try
        # the request 5 times instead of 3
        async def decorated_request(tries=3, timeout=10, **kwargs):
            while True:
                try:
                    with aiohttp.Timeout(timeout):
                        return await request(**kwargs)

                except peony.exceptions.RateLimitExceeded as e:
                    try:
                        return backup_client.request(**kwargs)
                    except:
                        delay = int(e.reset_in) + 1
                        fmt = "sleeping for {}s (rate limit exceeded on endpoint {})"
                        print(fmt.format(delay, kwargs['url']), file=sys.stderr)
                        await asyncio.sleep(delay)
                except asyncio.TimeoutError:
                    pass
                except:
                    tries -= 1
                    if not tries:
                        raise

        return decorated_request


    client = PeonyClient(**creds, error_handler=error_handler)

You can also choose to not use an error handler and disable the default one by
setting the ``error_handler`` argument to ``None``.
If you want to disable the global error handling for a specific request pass a
``_error_handling`` argument to this request with a value of ``False``.
