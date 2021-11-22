#!/usr/bin/env python
from setuptools import setup


def setup_package():
    setup(use_scm_version={"fallback_version": "999"})


if __name__ == "__main__":
    setup_package()
