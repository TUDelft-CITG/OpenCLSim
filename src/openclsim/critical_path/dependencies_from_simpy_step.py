"""
module contains
- class DependenciesFromSimpy that inherits from critical_path.base_cp.BaseCP

TODO Later we need to add this or make new module
- class MyCustomSimpyEnv that inherits from simpy.env and patches env.step()
"""

from openclsim.critical_path.base_cp import BaseCP


class DependenciesFromSimpy(BaseCP):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_dependency_list(self):
        """
        Get dependencies from simpy logging by analysing
        the data as saved with the patched env.step function

        requires self.env (instance MyCustomSimpy)

        Returns
        -------
        dependency_list : list
            list of tuples like [(A1, A2), (A1, A3), (A3, A4)]
            where A2 depends on A1 (A1 'causes' A2) et cetera
        """
        assert isinstance(
            self.env, MyCustomSimpyEnv
        ), "This module is not callable with the default simpy environment"

        # ...
        return []


class MyCustomSimpyEnv:
    """TODO SCOPE 6"""

    pass
