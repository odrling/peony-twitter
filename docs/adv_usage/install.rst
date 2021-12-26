.. _adv_install:

=======================
 Advanced installation
=======================

When you install peony using this command::

    $ pip3 install peony-twitter[all]

You install some modules that you may not need. But before deciding to not
install these modules you need to know what will change if they are
not installed.


python-magic
------------

You can install it by running::

    $ pip3 install peony-twitter[magic]

or (if peony is already installed)::

    $ pip3 install python-magic

``python-magic`` is used to find the mimetype of a file.
The mimetype of a media has to be given when making a multipart upload.
If you don't install this module you will not be able to send large pictures
or GIFs from a file path that would not be recognized by the ``mimetypes``
module (shipped with Python) or from a file object.


aiofiles
--------

You can install it by running::

    $ pip3 install peony-twitter[aiofiles]

or directly::

    $ pip3 install aiofiles


When this is installed every file will be opened using aiofiles, thus every
read operation will not block the event loop.

.. note::
    magic and aiofiles can be installed using the ``media`` extra requirement::

        $ pip3 install peony-twitter[media]

aiohttp
-------

This command will install some optional dependencies of aiohttp::

    $ pip3 install peony-twitter[aiohttp]

or again directly::

    $ pip3 install cchardet aiodns

This will install cchardet and aiodns, which could speed up aiohttp.


Minimal installation
--------------------

If you don't need these modules you can run::

    $ pip3 install peony-twitter

You can install these modules later if you change your mind.
