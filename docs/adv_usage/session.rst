================================
 Use an already created session
================================

If you use aiohttp to make requests on other websites you can pass on the
:class:`aiohttp.ClientSession` object to the :class:`~peony.client.PeonyClient`
on initialisation as the `session` argument.

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
        asyncio.run(client_with_session())
