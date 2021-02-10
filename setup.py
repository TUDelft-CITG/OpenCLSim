#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Setup file for openclsim.

    This file was generated with PyScaffold 2.5.6, a tool that easily
    puts up a scaffold for your new Python project. Learn more under:
    http://pyscaffold.readthedocs.org/
"""
# import os
import sys

from pkg_resources import VersionConflict, require
from setuptools import setup

try:
    require("setuptools>=38.3")
except VersionConflict:
    print("Error: version of setuptools is too old (<38.3)!")
    sys.exit(1)


def setup_package():
    needs_sphinx = {"build_sphinx", "upload_docs"}.intersection(sys.argv)
    sphinx = ["sphinx"] if needs_sphinx else []
    setup(
        setup_requires=["six", "pyscaffold"] + sphinx, use_pyscaffold=True
    )



if __name__ == "__main__":
    setup_package()
