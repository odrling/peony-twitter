#!/usr/bin/env python3

import asyncio
import io
import os.path
from concurrent.futures import ProcessPoolExecutor
from urllib.parse import urlparse

import aiofiles

try:
    import PIL.Image
except ImportError:
    PIL = None

try:
    from . import api, peony
except (SystemError, ImportError):
    import api
    from __init__ import peony, utils

client = peony.PeonyClient(**api.keys)


def convert(img, formats):
    """
        Convert the image to all the formats specified
    Parameters
    ----------
    img : PIL.Image.Image
        The image to convert
    formats : list
        List of all the formats to use
    Returns
    -------
    io.BytesIO
        A file object containing the converted image
    """
    media = None
    min_size = 0

    for kwargs in formats:
        f = io.BytesIO()
        if img.mode == "RGBA" and kwargs["format"] != "PNG":
            # convert to RGB if picture is too large as a png
            # this implies that the png format is the first in `formats`
            if min_size < 5 * 1024**2:
                continue
            else:
                img.convert("RGB")

        img.save(f, **kwargs)
        size = f.tell()

        if media is None or size < min_size:
            if media is not None:
                media.close()

            media = f
            min_size = size
        else:
            f.close()

    return media


def optimize_media(file_, max_size, formats):
    """
        Optimize an image
    Resize the picture to the ``max_size``, defaulting to the large
    photo size of Twitter in :meth:`PeonyClient.upload_media` when
    used with the ``optimize_media`` argument.
    Parameters
    ----------
    file_ : file object
        the file object of an image
    max_size : :obj:`tuple` or :obj:`list` of :obj:`int`
        a tuple in the format (width, height) which is maximum size of
        the picture returned by this function
    formats : :obj`list` or :obj:`tuple` of :obj:`dict`
        a list of all the formats to convert the picture to
    Returns
    -------
    file
        The smallest file created in this function
    """
    if not PIL:
        msg = "Pillow must be installed to optimize a media\n" "$ pip3 install Pillow"
        raise RuntimeError(msg)

    img = PIL.Image.open(file_)

    # resize the picture (defaults to the 'large' photo size of Twitter
    # in peony.PeonyClient.upload_media)
    ratio = max(hw / max_hw for hw, max_hw in zip(img.size, max_size))

    if ratio > 1:
        size = tuple(int(hw // ratio) for hw in img.size)
        img = img.resize(size, PIL.Image.ANTIALIAS)

    media = convert(img, formats)

    # do not close a file opened by the user
    # only close if a filename was given
    if not hasattr(file_, "read"):
        img.close()

    return media


async def process_media(media, path):
    data = await media.read()
    mime_type = await utils.get_type(data, path)
    if not mime_type.startswith("image"):
        return media

    # formats to try when converting the picture
    formats = [dict(format="PNG"), dict(format="JPEG", quality=90, optimize=True)]

    return await client.loop.run_in_executor(
        ProcessPoolExecutor(), optimize_media, io.BytesIO(data), (2048, 2048), formats
    )


async def send_tweet_with_media():
    # read the tweet's status
    status = input("status: ")

    path = ""
    while not path and not os.path.exists(path):
        path = input("file to upload:\n")

    # read the most common input formats
    path = urlparse(path).path.strip(" \"'")

    async with aiofiles.open(path, "rb") as media:
        # optimize pictures if PIL is available
        if PIL:
            media = await process_media(media, path)

        uploaded = await client.upload_media(media, chunk_size=2**18, chunked=True)
        media_id = uploaded.media_id
        await client.api.statuses.update.post(status=status, media_ids=media_id)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_tweet_with_media())
