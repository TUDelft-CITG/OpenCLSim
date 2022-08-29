"""
import other testcases as functions and show matplotlib gannt chart
"""
import matplotlib.pyplot as plt
# external dependencies for some extra plotting
import networkx as nx

from cases.scenario_container_level_dependency import (
    getActivitiesAndObjects as get_act_obj_level_dep,
)
from cases.scenario_delay import getActivitiesAndObjects as get_act_obj_delay
from cases.scenario_parallel_in_while import (
    getActivitiesAndObjects as scenario_par_while,
)
# preprogrammed simulations
from cases.scenario_resource_dependency import (
    getActivitiesAndObjects as get_act_obj_res_dep,
)
from cases.scenario_weather import getActivitiesAndObjects as get_act_obj_weather
from cases.scenario_weather import make_meteo_df
# openclsim
from openclsim.plot.critical_path_log import CpLog
from openclsim.plot.graph_dependencies import DependencyGraph

print("Case with resource limitations")
list_activities, list_objects = get_act_obj_res_dep()
my_cp_log_r = CpLog(list_objects, list_activities)
my_cp_log_r.get_dependencies()
my_cp_log_r.mark_critical_activities()
my_cp_log_r.make_gantt_mpl()
dep_G = DependencyGraph(list_activities)
fig, ax = plt.subplots(1, 1)
nx.draw(dep_G.G, ax=ax)

print("Case with container level dependency")
list_activities_level, list_objects_level = get_act_obj_level_dep(scenario=2)
my_cp_log_l = CpLog(list_objects_level, list_activities_level)
my_cp_log_l.get_dependencies()
my_cp_log_l.mark_critical_activities()
my_cp_log_l.make_gantt_mpl()

print("Case with relative delay/plugin")
list_activities_delay, list_objects_delay = get_act_obj_delay(scenario=1)
my_cp_log_d = CpLog(list_objects_delay, list_activities_delay)
my_cp_log_d.get_dependencies()
my_cp_log_d.mark_critical_activities()
my_cp_log_d.make_gantt_mpl()

print("Case with weather delay/plugin")
list_activities_w, list_objects_w = get_act_obj_weather()
my_cp_log_w = CpLog(list_objects_w, list_activities_w)
my_cp_log_w.get_dependencies()
my_cp_log_w.mark_critical_activities()
my_cp_log_w.make_gantt_mpl()
df_meteo = make_meteo_df()
fig, ax = plt.subplots(1, 1)
ax.plot(df_meteo.index, df_meteo.loc[:, "Hs"])


print("Case with parallel in while")
list_activities_p, list_objects_p = scenario_par_while()
my_cp_log_par = CpLog(list_objects_p, list_activities_p)
my_cp_log_par.get_dependencies()
my_cp_log_par.mark_critical_activities()
my_cp_log_par.make_gantt_mpl()
dep_G = DependencyGraph(list_activities_p)
fig, ax = plt.subplots(1, 1)
nx.draw(dep_G.G, ax=ax)
