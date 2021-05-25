[![Documentation](https://img.shields.io/badge/sphinx-documentation-informational.svg)](https://openclsim.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-informational.svg)](https://github.com/TUDelft-CITG/OpenCLSim/blob/master/LICENSE.txt)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.3730615.svg)](https://doi.org/10.5281/zenodo.3730615)

[![TUDelft-CITG](https://circleci.com/gh/TUDelft-CITG/OpenCLSim.svg?style=shield&circle-token=fc95d870dc21fdf11e1ebc02f9defcd99212197a)](https://circleci.com/gh/TUDelft-CITG/OpenCLSim)
[![Coverage](https://artifact-getter.herokuapp.com/get_coverage_badge?circle_url=https://circleci.com/gh/TUDelft-CITG/OpenCLSim&circle_token=fc95d870dc21fdf11e1ebc02f9defcd99212197a=str)](https://artifact-getter.herokuapp.com/get_coverage_report?circle_url=https://circleci.com/gh/TUDelft-CITG/OpenCLSim&circle_token=fc95d870dc21fdf11e1ebc02f9defcd99212197a)

# OpenCLSim

**Open** source **C**omplex **L**ogistics **Sim**ulation - Rule driven scheduling of cyclic activities for in-depth comparison of alternative operating strategies.

Documentation is found [here](https://openclsim.readthedocs.io).

## Installation

To install OpenCLSim, run this command in your terminal. This is the preferred method to install OpenCLSim, as it will always install the most recent stable release. In general you want to install python software in a virtual environment, either using [anaconda](https://docs.anaconda.com/anaconda/install/) or through python's default [virtual environment](https://docs.python.org/3/tutorial/venv.html).

``` bash
pip install openclsim
```

Make sure you also install the  dependencies, which are recorded in the file `requirements.txt`.
If you have an anaconda setup, you can use the following command:

``` bash
conda install --file requirements.txt
```

If you are using a pip based environment, you can install the requirements with pip:
``` bash
pip install -r requirements.txt
```

If you do not have [pip](https://pip.pypa.io) installed, this [Python installation guide](http://docs.python-guide.org/en/latest/starting/installation/) can guide you through the process. You can read the [documentation](https://openclsim.readthedocs.io/en/latest/installation.html) for other installation methods.

## Examples

The benefit of OpenCLSim is the generic set-up. This set-up allows the creation of complex logistical flows. A number of examples are presented in a seperate [Jupyter Notebook repository](https://github.com/TUDelft-CITG/OpenCLSim-Notebooks). Information on how to use the notebooks is presented in that repository as well.
