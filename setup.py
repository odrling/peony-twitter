#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import inspect
import os
import re
import sys

from setuptools import find_packages, setup


def get_metadata(metadatafile):
    with open(metadatafile) as stream:
        text = stream.read()

        ex = r"__(\w*?)__\s*?=\s*?[\"\']([^\"\']*)"
        items = re.findall(ex, text)
        metadata = {key: value for key, value in items}

        metadata['keywords'] = metadata.get('keywords', '').split(', ')

        ex = r'"{3}[^\w]*(?P<name>[^\s]*)[^\w]+(?P<description>.*)'
        match = re.search(ex, text)

        package_info = {key: value.strip()
                        for key, value in match.groupdict().items()}
        metadata.update(re.search(ex, text).groupdict())

    return metadata


ex = r"# ([^\s:]+).*\n([^#]+)"
requirements_prog = re.compile(ex)


def get_requirements(requirements):
    with open(requirements) as stream:
        matches = requirements_prog.findall(stream.read())
        requires = {key: value.strip().splitlines()
                    for key, value in matches}

    return requires


def main():
    if sys.version_info < (3, 5):
        raise RuntimeError("Peony requires Python 3.5+")

    dirname = os.path.dirname(inspect.getfile(inspect.currentframe()))

    # get metadata and keywords from peony/__init__.py
    metadata = get_metadata(os.path.join(dirname, 'peony', '__init__.py'))

    # get requirements from requirements.txt
    requires = get_requirements(os.path.join(dirname, 'requirements.txt'))

    # get extras requirements from extras_require.txt
    extras = os.path.join(dirname, 'extras_require.txt')
    extras_require = get_requirements(extras)

    # get long description from README.md
    with open('README.rst') as stream:
        long_description = stream.read()

    setup(
        long_description=long_description,
        packages=find_packages(include=["peony*"]),
        **metadata,
        **requires,
        extras_require=extras_require
    )


if __name__ == '__main__':
    main()
