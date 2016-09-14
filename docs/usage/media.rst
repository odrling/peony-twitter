===============
 Upload medias
===============

You can easily upload a media with peony:

.. code-block:: python

    import asyncio
    from peony import PeonyClient

    # creds being a dictionnary containing your api keys
    client = PeonyClient(**creds)

    async def upload_media(picture="picture.jpg"):
        media = await client.upload_media(path, auto_convert=True)
        client.api.statuses.update.post(status="Wow! Look at this picture!",
                                        media_ids=[media.media_id])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(upload_media="picture.jpg")

.. note:: The auto_convert argument of :func:`peony.PeonyClient.upload_media`
          can be used if you want to convert your picture to the format that
          gives the smallest size. It also resizes the picture to the
          'large' photo size of Twitter (1024x2048 at the time of writing)
