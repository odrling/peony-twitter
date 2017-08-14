===============
 Upload medias
===============

You can easily upload a media with peony:

.. code-block:: python

    import asyncio
    from peony import PeonyClient

    # creds being a dictionnary containing your api keys
    client = PeonyClient(**creds)

    async def upload_media(path):
        media = await client.upload_media(path)
        client.api.statuses.update.post(status="Wow! Look at this picture!",
                                        media_ids=[media.media_id])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(upload_media("picture.jpg"))


.. note::

    :meth:`~peony.client.PeonyClient.upload_media` has a ``chunked`` parameter
    that is the "recommended way" to upload a media on Twitter.
    This allows to upload video and large gifs on Twitter and could help in
    case of bad connection (only a chunk to reupload).
    You can set the ``chunk_size`` parameter to specify the size of a chunk in
    bytes.
    You can specify the mime type of the media using the ``media_type``
    parameter and the Twitter media category using the ``media_category``
    of the media (in case that could not be guessed from the mime type by peony)

You can also use an url:

.. code-block:: python

    async def upload_from_url():
        media = await client.upload_media("http://some.domain.com/pic.jpg")
        # ...


or an aiohttp request:

.. code-block:: python

    async def upload_from_url():
        async with aiohttp.ClientSession() as session:
            async with session.get("http://some.domain.com/pic.jpg") as req:
                media = await client.upload_media("http://some.domain.com/pic.jpg")

.. note::

    This is actually what passing the url to upload_media does but creates a
    new session instead of using an existing session. You shouldn't have any
    reason to use this.

or a file object:

.. code-block:: python

    async def upload_from_file():
        with open("picture.jpg") as file:
            media = await client.upload_media(file)
        # ...

.. note::

    It is recommended to use ``aiofiles`` if you are planning to work with
    files.

or even bytes:

.. code-block:: python

    async def upload_from_bytes();
        with open("picture.jpg") as file:
            # there might be a better use case
            media = await client.upload_media(file.read())
