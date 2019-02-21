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
    require('setuptools>=38.3')
except VersionConflict:
    print("Error: version of setuptools is too old (<38.3)!")
    sys.exit(1)

requires = [
    "pandas",
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
    "Flask",
    "Flask-cors"
]

setup_requirements = [
    "pytest-runner",
]

tests_require = [
    "pytest",
    "pytest-cov",
]


setup(
    author="Mark van Koningsveld",
    author_email="m.vankoningsveld@tudelft.nl",
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="The Digital Twin package aims to facilitate basic nautical traffic simulations.",
    entry_points={
        'console_scripts': [
            'digital_twin=digital_twin.cli:cli',
        ],
    },
    install_requires=requires,
    long_description="",  # README + '\n\n' + CHANGES,
    include_package_data=True,
    keywords="Digital Twin",
    name="digital_twin",
    packages=find_packages(include=["digital_twin"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=tests_require,
    url="https://github.com/TUDelft-CITG/digital_twin",
    version="0.2.0",
    zip_safe=False,
)
