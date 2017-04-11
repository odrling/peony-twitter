# -*- coding: utf-8 -*-
""" load the module at the root of the repository """

import os
import inspect
import sys

file_ = os.path.abspath(inspect.getfile(inspect.currentframe()))
testdir = os.path.dirname(file_)

sys.path.insert(0, os.path.dirname(testdir))
