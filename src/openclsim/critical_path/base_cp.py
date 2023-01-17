"""
module with BaseCp class that has (non abstract) methods
wrt finding the critical path of the simulation


Toelichting @Pieter:
- deze module was jouw initiele architecture.py
- ik heb de functionaliteit over diverse modules gesplitst.
    Het lijkt mij logisch dit onder critical_path te doen en niet onder plot
-  based on initial commit approx
    250 lines for make_recorded_activities (SCOPE 2)
    400 lines for simulation_graph (aka 'ActivityGraph'), (SCOPE 3)
    100 lines for 'dependencies_from_recorded_activities' (SCOPE 4)
    900 lines for 'dependencies_from_model' (SCOPE 5)
        eventueel kan DependencyGraph nog zijn eigen module krijgen dan splitten we 250 lines af EN
        DependencyGraph is wat robuuster/zou mogelijk in andere toepassingen ook worden gebruikt.
    UNKNOWN lines for 'dependencies_from_simpy_step' (maar zeg 100-200) (SCOPE 6)
    UNKNOWN lines for netjes simpy logging patch maken/implementeren (maar zeg 200-300) (SCOPE 6)
- NAAMGEVINGEN
    - simulation_graph/SimulationGraph maakt een graaf van de simulatie (dus
    alle recorded activiteiten 'instances', afhankelijkheden en hun simulatietijden)
    en kan het kritieke pad vinden
    - base_cp/BaseCP: de baseclass voor het vinden van dependencies,
    maken van overzicht recorded_activities en vinden kritieke pad.
    - de drie methoden om dependencies te vinden hebben dan ook nog eigen module/class

"""

from abc import ABC, abstractmethod

from openclsim.critical_path.simulation_graph import SimulationGraph


class BaseCP(ABC):
    """
    base class for critical path

    Parameters
    ------------
    env : instance of simpy.env or instance of class that inherits from simpy.env
    object_list : list of all (simulation) objects with Log mixin (after simulation)
    activity_list : list of all (simulation) activities with Log mixin (after simulation)
    """

    def __init__(
        self,
        env,
        object_list,
        activity_list,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        # some asserts
        self.env = env
        self.object_list = object_list
        self.activity_list = activity_list

        # init attributes which will be set by (child) methods
        self.recorded_activities_df = None
        self.dependency_list = None
        self.simulation_graph = None

    @abstractmethod()
    def get_dependency_list(self):
        """must be implemented by child classes"""
        return []

    def _make_recorded_activities_df(self):
        """
        set a recorded_activity_df in self
        uses the logs of provided activities and sim objects, combines these, adds unique UUID
        and reshape into format such that single row has a start time and an end time

        Notes
        ------
        in original commit approx 250 lines of code (split over several functions)
        """
        pass

    def get_recorded_activity_df(self):
        """ get a recorded_activity_df in self"""
        if self.recorded_activities_df is None:
            self._make_recorded_activities_df()
        return self.recorded_activities_df

    def __make_simulation_graph(self):
        """use self.recorded_activity_df and self.dependency_list to build graph of
        (interconnected) activities as evaluated in time in simulation"""
        self.simulation_graph = SimulationGraph(self.recorded_activities_df, self.dependency_list)

    def get_critical_path_df(self):
        """
        enrich recorded activity df with column 'is_critical' and return this dataframe
        """
        self._make_recorded_activities_df()  # makes self.recorded_activities_df
        self.dependency_list = self.get_dependency_list()
        self.__make_simulation_graph()  # makes self.activity_graph

        return self.__compute_critical_path()

    def __compute_critical_path(self):
        """
        provided self has an simulation graph based on all the recorded activities and
        dependencies, compute the critical path, i.e. mark all activities which are on (any)
        critical path as critical.
        """
        return []


"""
# example production code:

my_env = MyCustomSimpyEnv()
# OR
my_env = simpy.Environment()

# simulation code
# ...

# call CP functionality
cp_log = DependenciesFromModel(...)  # OR 1 of other classes that inherits 
critical_path_df = cp_log.get_critical_path_df()
plot.gantt_chart(critical_path_df)
"""


"""
OUTLINE SCOPES

scope1: architectuur
scope2: `get_recorded_activity_df`
scope3: `get_activity_graph` + `compute_critical_path`
scope4: `DependenciesFromLog`
scope5: `DependenciesFromModel`
scope6: `DependenciesFromSimpy`
"""