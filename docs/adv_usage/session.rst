================================
 Use an already created session
================================

If you use aiohttp to make requests on other websites you can pass on the
:class:`aiohttp.ClientSession` object to the :class:`PeonyClient` on initialisation
as the `session` argument.

.. code-block:: python

    import asyncio

    import aiohttp
    from peony import PeonyClient

    async def client_with_session():
        async with aiohttp.ClientSession() as session:
            # The client will use the session to make requests
            client = PeonyClient(**creds, session=session)
            await client.run_tasks()

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(client_with_session())


.. warning::

    Don't delete the :class:`PeonyClient` instance if you need to use the
    session later in your program, as doing so would close the session.


