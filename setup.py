#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Setup file for hydraulic_infrastructure_realisation.
    Use setup.cfg to configure your project.

    This file was generated with PyScaffold 3.1.
    PyScaffold helps you to put up the scaffold of your new Python project.
    Learn more under: https://pyscaffold.org/
"""
import sys

from pkg_resources import require, VersionConflict
from setuptools import setup, find_packages

try:
    require("setuptools>=38.3")
except VersionConflict:
    print("Error: version of setuptools is too old (<38.3)!")
    sys.exit(1)

requires = [
    "pandas>=0.24.0",
    "numpy",
    "simpy",
    "networkx",
    "shapely",
    "scipy",
    "click",
    "matplotlib",
    "pint",
    "pyproj",
    "plotly",
    "simplekml",
    "nose",
    "Flask>=1.0",
    "Flask-cors",
    "sphinx_rtd_theme",
    "Dill",
]

setup_requirements = ["pytest-runner"]

tests_require = ["pytest", "pytest-cov", "pytest-timeout", "pytest-datadir"]

with open("README.md", "r") as des:
    long_description = des.read()

setup(
    author="Mark van Koningsveld",
    author_email="m.vankoningsveld@tudelft.nl",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
    ],
    description="The OpenCLSim package aims to facilitate rule based planning of cyclic activities and in depth comparison of different system concepts.",
    entry_points={"console_scripts": ["openclsim=openclsim.cli:cli"]},
    install_requires=requires,
    long_description=long_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="OpenCLSim",
    name="openclsim",
    packages=["openclsim", "openclsim.model"],
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=tests_require,
    url="https://github.com/TUDelft-CITG/openclsim",
    version="v1.3.0a26",
    zip_safe=False,
)
