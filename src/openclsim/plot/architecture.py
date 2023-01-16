from abc import ABC, abstract_method

class BaseCpLog(ABC):

    def __init__(
        self,
        env,
        registry,
        object_list,
        activity_list,
        *args,
        **kwars,
    ):
        super().__init__(*args, **kwargs)

        self.env = env
        self.registry = registry
        self.object_list = object_list
        self.activity_list = activity_list


    @abstract_method()
    def get_dependency_list(self, activity_instances):
        return []

    def get_recorded_activity_df(self):
        pass

    def get_activity_graph(self):
        pass

    def get_critical_path(self):
        recorded_activity_df = self.get_recorded_activity_df()
        dependency_list = self.get_dependency_list(self.recorded_activity_df)
        self.activity_graph = self.get_activity_graph(dependency_list)

        return self.compute_critical_path()

    def compute_critical_path(self):
        return []

class DependenciesFromModel(BaseCpLog):
    def __init__(self, model, *args, **kwars):
        super().__init__(*args, **kwargs)

        self.model = model

    def get_dependency_list(self, dependency_list):
        # ...
        return []

class DependenciesFromLog(BaseCpLog):
    def __init__(self, *args, **kwars):
        super().__init__(*args, **kwargs)

    def get_dependency_list(self, dependency_list):
        # ...
        return []

class DependenciesFromSimpy(BaseCpLog):
    def __init__(self, *args, **kwars):
        super().__init__(*args, **kwargs)

    def get_dependency_list(self, dependency_list):
        assert(
            isinstance(self.env, MyCustomSimpy),
            "This module is not callable with the default simpy environment"
        )
        # ...
        return []

cp_log = DependenciesFromModel(...)
critical_path = cp_log.get_critical_path()
plot.gantt_chart(critical_path)

"""
scope1: architectuur
scope2: `get_recorded_activity_df`
scope3: `get_activity_graph` + `compute_critical_path`
scope4: `DependenciesFromLog`
scope5: `DependenciesFromModel`
scope6: `DependenciesFromSimpy`
"""