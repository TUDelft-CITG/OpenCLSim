# -*- coding: utf-8 -*-
"""
Created on Wed May  6 21:57:21 2020

@author: andre
"""
import datetime, time
import simpy

import pandas as pd
import openclsim.core as core
import openclsim.model as model
import openclsim.plot as plot

simulation_start = 0

my_env = simpy.Environment(initial_time=simulation_start)
registry = {}
keep_resources = []

reporting_activity_data = {
    "env": my_env,
    "name": "Reporting activity",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",  # For logging purposes
    "registry": registry,
    "duration": 0,
    "postpone_start": False,
    "keep_resources": keep_resources,
}
reporting_activity = model.BasicActivity(**reporting_activity_data)

sub_processes = []
basic_activity_data1 = {
    "env": my_env,
    "name": "Basic activity1",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
    "registry": registry,
    "duration": 14,
    "postpone_start": True,
    "additional_logs": [reporting_activity],
    "keep_resources": keep_resources,
}
sub_processes.append(model.BasicActivity(**basic_activity_data1))
basic_activity_data2 = {
    "env": my_env,
    "name": "Basic activity2",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5c",  # For logging purposes
    "registry": registry,
    "duration": 5,
    "additional_logs": [reporting_activity],
    "postpone_start": True,
    "keep_resources": keep_resources,
}
sub_processes.append(model.BasicActivity(**basic_activity_data2))
basic_activity_data3 = {
    "env": my_env,
    "name": "Basic activity3",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5d",  # For logging purposes
    "registry": registry,
    "duration": 220,
    "additional_logs": [reporting_activity],
    "postpone_start": True,
    "keep_resources": keep_resources,
}
sub_processes.append(model.BasicActivity(**basic_activity_data3))

sequential_activity_data = {
    "env": my_env,
    "name": "Sequential process",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff60",  # For logging purposes
    "registry": registry,
    "sub_processes": (proc for proc in sub_processes),
    "keep_resources": keep_resources,
}
activity = model.SequentialActivity(**sequential_activity_data)

my_env.run()

log_df = pd.DataFrame(activity.log)
data = log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]

basic = []
for proc in sub_processes:
    df = pd.DataFrame(proc.log)
    basic.append(df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]])

rep_log_df = pd.DataFrame(reporting_activity.log)
data_rep = rep_log_df[["Message", "ActivityState", "Timestamp", "Value", "ActivityID"]]
data_rep = data_rep.drop_duplicates()