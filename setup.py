#!/usr/bin/env python3

import os
import sys
import re

from setuptools import setup, find_packages


def get_metadata(metadatafile):
    with open(metadatafile) as stream:
        text = stream.read()

        ex = "__(.*?)__ *?= *?[\"\'](.*?)[\"\']"
        items = re.findall(ex, text)
        metadata = {key: value for key, value in items}

        metadata['keywords'] = metadata.get('keywords', '').split(', ')

        ex = '"""[ \n]*(?P<name>.*)[ \n](?P<description>.*)'
        metadata.update(re.search(ex, text).groupdict())

    return metadata


def get_requirements(requirementsfile, key=""):
    with open(requirementsfile) as stream:
        prog = re.compile("(?:# (?P<key>\S+)|(?P<value>\S+))")
        requires = {}

        for match in (i.groupdict() for i in prog.finditer(stream.read())):
            if match['key'] is not None:
                key = match['key']
                if key not in requires:
                    requires[key] = []
            elif match['value'] is not None and key:
                requires[key].append(match['value'])

    return requires


def main():
    if sys.version_info < (3, 5):
        raise RuntimeError("Peony requires Python 3.5+")

    # calling this file from another directory should work as expected
    os.chdir(os.path.dirname(__file__))

    # get metadata and keywords from peony/__init__.py
    metadata = get_metadata(os.path.join('peony', '__init__.py'))

    # get requirements from requirements.txt
    requires = get_requirements('requirements.txt')

    # get long description from README.md
    with open('README.md') as stream:
        long_description = stream.read()

    setup(
        long_description=long_description,
        packages=find_packages(include=["peony*"]),
        **metadata,
        **requires
    )


if __name__ == '__main__':
    main()
