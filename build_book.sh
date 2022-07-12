#!/bin/sh
# Copy the examples from the notebooks
cp notebooks/*.ipynb book/examples/
# Copy the api docs from the docs folder
cp docs/openclsim.rst book/docs
# Copy the Authors list from the root folder
cp AUTHORS.rst book/docs/
# Copy logos
cp -r docs/_static book/docs/
jupyter-book build book
