[![CircleCI](https://circleci.com/gh/TUDelft-CITG/Hydraulic-Infrastructure-Realisation.svg?style=svg&circle-token=fc95d870dc21fdf11e1ebc02f9defcd99212197a)](https://circleci.com/gh/TUDelft-CITG/Hydraulic-Infrastructure-Realisation)

[![Coverage](https://oedm.vanoord.com/proxy/circleci_no_redirect/github/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/master/latest/3b00333d4fe20c813bd9bc81ce2e1d4f5fae987a/tmp/artifacts/coverage.svg)](https://oedm.vanoord.com/proxy/circleci_no_redirect/github/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/master/latest/3b00333d4fe20c813bd9bc81ce2e1d4f5fae987a/tmp/artifacts/index.html)
[ ![Documentation](https://img.shields.io/badge/sphinx-documentation-brightgreen.svg)](https://oedm.vanoord.com/proxy/circleci_no_redirect/github/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/master/latest/3b00333d4fe20c813bd9bc81ce2e1d4f5fae987a/tmp/artifacts/docs/index.html)
[ ![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://github.com/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/blob/master/LICENSE.txt)

# Hydraulic-Infrastructure-Realisation

Complex Logistics Simulation - Rule based planning of cyclic activities for in-depth comparison of different system concepts.

Documentation can be found [here](https://oedm.vanoord.com/proxy/circleci_no_redirect/github/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/master/latest/3b00333d4fe20c813bd9bc81ce2e1d4f5fae987a/tmp/artifacts/docs/index.html).

## Installation

OpenCLSim is available on [pypi](https://pypi.org/project/openclsim/), this allows easy installation using pip. You can read the [documentation](https://oedm.vanoord.com/proxy/circleci_no_redirect/github/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/master/latest/3b00333d4fe20c813bd9bc81ce2e1d4f5fae987a/tmp/artifacts/docs/installation.html) for other installation methods.

``` bash
pip install openclsim
```

## Example notebooks

The benefit of OpenCLSim is the generic set-up. This set-up allows the creation of complex logistical flows. A number of examples are presented in the [notebooks folder](https://github.com/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/tree/master/notebooks). You can run them locally or as an [Azure notebook](https://notebooks.azure.com/home/projects).

## Start server

A flask server is part of the OpenCLSim package. The example code below lets you start the Flask server from the windows command line, for other operation systems please check the [Flask Documentation](http://flask.pocoo.org/docs/dev/cli/).

``` bash
# Set Flask app
set FLASK_APP=openclsim/server.py

# Set Flask environment
set FLASK_ENV=development

# Run Flask
flask run
```
