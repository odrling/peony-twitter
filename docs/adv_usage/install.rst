.. _adv_install:

=======================
 Advanced installation
=======================

When you install peony using this command::

    $ pip3 install peony-twitter[all]

You install some modules that you may not need. But before deciding to not
install these modules you need to know what will change if they are
not installed.


magic-python
------------

You can install it by running::

    $ pip3 install peony-twitter[magic]

or (if peony is already installed)::

    $ pip3 install magic-python

``magic-python`` is used to find the mimetype of a file.
The mimetype of a media has to be given when making a multipart upload.
If you don't install this module you will not be able to send large pictures
or GIFs from a file path that would not be recognized by the ``mimetypes``
module (shipped with Python) or from a file object.


Pillow
------

You can install it by running::

    $ pip3 install peony-twitter[Pillow]

or (if peony is already installed)::

    $ pip3 install Pillow

``Pillow`` is used when setting the ``auto_convert`` parameter of
:meth:`PeonyClient.upload_media` to ``True`` to resize the picture and use
the better suited format for the media.


Minimal installation
--------------------

If you don't need these modules you can run::

    $ pip3 install peony-twitter

You can install these modules later if you change your mind.
