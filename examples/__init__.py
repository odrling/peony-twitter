
import inspect
import os
import sys


file_ = os.path.abspath(inspect.getfile(inspect.currentframe()))
testdir = os.path.dirname(file_)

sys.path.insert(0, os.path.dirname(testdir))


import peony  # noqa
from peony import utils  # noqa


try:
    try:
        from . import api  # noqa
    except (SystemError, ImportError):
        import api  # noqa
except ImportError:
    print("You must set your keys in the file example/api.py."
          "\nCopy/paste the file api_example.py and set your "
          "keys as indicated.")

    exit()


msg = "peony v" + peony.__version__
msg += "\n" + "-" * len(msg)
print(msg)
