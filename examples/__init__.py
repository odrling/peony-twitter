
import os
import inspect
import sys

try:
    try:
        from . import api
    except (SystemError, ImportError):
        import api
except ImportError:
    print("You must set your keys in the file example/api.py."
          "\nCopy/paste the file api_example.py and set your "
          "keys as indicated.")

    exit()


file_ = os.path.abspath(inspect.getfile(inspect.currentframe()))
testdir = os.path.dirname(file_)

sys.path.insert(0, os.path.dirname(testdir))

import peony
print("peony v" + peony.__version__)
