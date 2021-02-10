"""Top-level package for OpenCLSim."""

# import pkg_resources

import openclsim.core as core
import openclsim.model as model
import openclsim.plot as plot
import openclsim.plugins as plugins

__author__ = """Mark van Koningsveld"""
__email__ = "M.vanKoningsveld@tudelft.nl"
__version__ = "v1.4.2"
__all__ = ["model", "plugins", "core", "plot"]
# __version__ = pkg_resources.get_distribution(__name__).version
