[![CircleCI](https://circleci.com/gh/TUDelft-CITG/Hydraulic-Infrastructure-Realisation.svg?style=svg&circle-token=fc95d870dc21fdf11e1ebc02f9defcd99212197a)](https://circleci.com/gh/TUDelft-CITG/Hydraulic-Infrastructure-Realisation)

[![Coverage](https://oedm.vanoord.com/proxy/circleci_no_redirect/github/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/master/latest/3b00333d4fe20c813bd9bc81ce2e1d4f5fae987a/tmp/artifacts/coverage.svg)](https://oedm.vanoord.com/proxy/circleci_no_redirect/github/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/master/latest/3b00333d4fe20c813bd9bc81ce2e1d4f5fae987a/tmp/artifacts/index.html)
[ ![Documentation](https://img.shields.io/badge/sphinx-documentation-brightgreen.svg)](https://oedm.vanoord.com/proxy/circleci_no_redirect/github/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/master/latest/3b00333d4fe20c813bd9bc81ce2e1d4f5fae987a/tmp/artifacts/docs/index.html)
[ ![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://github.com/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/blob/master/LICENSE.txt)

Hydraulic-Infrastructure-Realisation
====================================

* Documentation can be found: [here](https://oedm.vanoord.com/proxy/circleci_no_redirect/github/TUDelft-CITG/Hydraulic-Infrastructure-Realisation/master/latest/3b00333d4fe20c813bd9bc81ce2e1d4f5fae987a/tmp/artifacts/docs/index.html)

Features
--------

Complex Logistics Simulation - Rule based planning of cyclic activities for in-depth comparison of different system concepts

Example notebooks:
* **Example 01 - Basic Hopper Operation** - Example of a trailing suction hopper dredge shipping sediment from origin to destination site.
* **Example 02 - Fuel Use** - Example of estimating fuel use on a project by keeping track of energy useage for each step of the production cycle.
* **Example 03 - Tracking Spill** - Example of a project where sediment spill limits influence project progress.
* **Example 04 - Building a Layered Dike** - Example of a construction challenge, with four separate activites, where each activity depends on the progress of the other activities.
* **Example 05 - Basic Hopper Operation on route** - Example of a trailing suction hopper dredge shipping sediment from origin to destination site while following a graph path.
* **Example 06 - Container Transfer Hub** - Example of a container transfer hub, where very large container vessels deliver containers, while smaller vessels take care of the distribution to the hinterland. Traffic follows a graph path.
* **Example 07 - Rebuild simulation from file** - Example of saving the simulation environment to a file. The code from example 01 is used, but *savesim.py* is introduced, which allows saving all parameters to a .pkl file, from which an exact copy can be simulated.

## Installation

Installation using *pip install digital_twin* is not yet available. Running following three lines in your command prompt will allow you installing the package as well:

``` bash
# Download the package
git clone https://github.com/TUDelft-CITG/Hydraulic-Infrastructure-Realisation

# Go to the correct folder
cd Hydraulic-Infrastructure-Realisation

# Install package
pip install -e .
```

## Start server

``` bash
# Set Flask app
set FLASK_APP=digital_twin/server.py

# Set Flask environment
set FLASK_ENV=development

# Run Flask
flask run
```

## Run app
Once the the Flask server is running and serving, you can start the Vue application.

``` bash
# Go to correct folder
cd app-Hydraulic-Infrastructure

# Run app
npm run serve
```

## Deploy to AWS

``` bash
pip install --upgrade awsebcli
eb init
eb deploy
```
