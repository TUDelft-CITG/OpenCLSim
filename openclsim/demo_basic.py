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
reporting_activity_data = {
    "env": my_env,
    "name": "Reporting activity",
    "ID": "6dbbbdf7-4589-11e9-bf3b-b469212bff5k",  # For logging purposes
    "registry": registry,
    "duration": 0,
    "postpone_start": False,
}
reporting_activity = model.BasicActivity(**reporting_activity_data)


basic_activity_data= {"env"  : my_env,
                      "name" : "Basic activity",
                      "registry": registry,
                      "ID":"6dbbbdf7-4589-11e9-bf3b-b469212bff5b",  # For logging purposes
                      "duration" : 14,
                      "additional_logs": [reporting_activity],
                      }
activity = model.BasicActivity(**basic_activity_data)

my_env.run(until=100)

log_df = pd.DataFrame(activity.log)
data =log_df[['Message', 'ActivityState', 'Timestamp', 'Value', 'ActivityID']]


