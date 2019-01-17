import pandas as pd
import numpy as np
import datetime

# plotting libraries
from plotly.offline import init_notebook_mode, iplot
import plotly.graph_objs as go

# spatial libraries 
import pyproj
import shapely.geometry
from simplekml import Kml, Style

import networkx as nx

def vessel_planning(vessels, activities, colors, web=False):
        """create a plot of the planning of vessels"""

        def get_segments(series, activity, y_val):
            """extract 'start' and 'stop' of activities from log"""
            x = []
            y = []
            for i, v in series.iteritems():
                if v == activity + ' start':
                    start = i
                if v == activity + ' stop':
                    x.extend((start, start, i, i, i))
                    y.extend((y_val, y_val, y_val, y_val, None))
            return x, y

        # organise logdata into 'dataframes' 
        dataframes = []
        for vessel in vessels:
            df = pd.DataFrame(
                {'log_value': vessel.value, 'log_string': vessel.log}, vessel.t)
            dataframes.append(df)
        df = dataframes[0]

        # prepare traces for each of the activities
        traces = []
        for i, activity in enumerate(activities):
            x_combined = []
            y_combined = []
            for k, df in enumerate(dataframes):
                y_val = vessels[k].name
                x, y = get_segments(
                    df['log_string'], activity=activity, y_val=y_val)
                x_combined.extend(x)
                y_combined.extend(y)
            traces.append(go.Scatter(
                name=activity,
                x=x_combined,
                y=y_combined,
                mode='lines',
                hoverinfo='y+name',
                line=dict(color=colors[i], width=10),
                connectgaps=False))
        
        # prepare layout of figure
        layout = go.Layout(
            title='Vessel planning',
            hovermode='closest',
            legend=dict(x=0, y=-.2, orientation="h"),
            xaxis=dict(
                title='Time',
                titlefont=dict(
                    family='Courier New, monospace',
                    size=18,
                    color='#7f7f7f'),
                range=[0, vessel.t[-1]]),
            yaxis=dict(
                title='Vessels',
                titlefont=dict(
                    family='Courier New, monospace',
                    size=18,
                    color='#7f7f7f')))
        
        # plot figure
        init_notebook_mode(connected=True)        
        fig = go.Figure(data=traces, layout=layout)
        return iplot(fig, filename='news-source')

def vessel_kml(env, vessels, 
               fname='vessel_movements.kml',
               icon='http://maps.google.com/mapfiles/kml/shapes/donut.png',
               size=1,
               scale=1,
               stepsize=120):
        """Create a kml visualisation of vessels. Env variable needs to contain 
        epoch to enable conversion of simulation time to real time. Vessels need
        logs that contain geometries in lat, lon as a function of time."""
 
        # create a kml file containing the visualisation
        kml = Kml()
        fol = kml.newfolder(name="Vessels")

        shared_style = Style()
        shared_style.labelstyle.color = 'ffffffff'  # White
        shared_style.labelstyle.scale = size  
        shared_style.iconstyle.color = 'ffff0000'  # Blue
        shared_style.iconstyle.scale = scale
        shared_style.iconstyle.icon.href = icon

        # each timestep will be represented as a single point
        for vessel in vessels:
            geom_x = []
            geom_y = []

            for geom in vessel.log["Geometry"]:
                geom_x.append(geom.x)
                geom_y.append(geom.y)

            vessel.log["Geometry - x"] = geom_x
            vessel.log["Geometry - y"] = geom_y
            
            time_stamp_min = min(vessel.log["Timestamp"])
            time_stamp_max = max(vessel.log["Timestamp"])

            steps = int(np.floor((time_stamp_max - time_stamp_min) / stepsize))

            timestamps_t = np.linspace(time_stamp_min, time_stamp_max, steps)
            vessel.log["timestamps_t"] = timestamps_t
            vessel.log["timestamps_x"] = np.interp(timestamps_t, vessel.log["Timestamp"], vessel.log["Geometry - x"])
            vessel.log["timestamps_y"] = np.interp(timestamps_t, vessel.log["Timestamp"], vessel.log["Geometry - y"])

            for log_index, value in enumerate(vessel.log["timestamps_t"][:-1]):
                
                begin = env.epoch + datetime.timedelta(seconds=vessel.log["timestamps_t"][log_index])
                end = env.epoch + datetime.timedelta(seconds=vessel.log["timestamps_t"][log_index + 1])
                
                pnt = fol.newpoint(name=vessel.name, coords=[(vessel.log["timestamps_x"][log_index], vessel.log["timestamps_y"][log_index])])
                pnt.timespan.begin = begin.isoformat()
                pnt.timespan.end = end.isoformat()
                pnt.style = shared_style

            # include last point as well
            begin = env.epoch + datetime.timedelta(seconds=vessel.log["timestamps_t"][log_index + 1])
            end = env.epoch + datetime.timedelta(seconds=vessel.log["timestamps_t"][log_index + 1])
           
            pnt = fol.newpoint(name=vessel.name, coords=[(vessel.log["timestamps_x"][log_index + 1], vessel.log["timestamps_y"][log_index + 1])])
            pnt.timespan.begin = begin.isoformat()
            pnt.timespan.end = end.isoformat()
            pnt.style = shared_style
                
        kml.save(fname)

def graph_kml(env, 
              fname='graph.kml',
              icon='http://maps.google.com/mapfiles/kml/shapes/donut.png',
              size=0.5,
              scale=0.5,
              width=5):
        """Create a kml visualisation of graph. Env variable needs to contain 
        graph."""
 
        # create a kml file containing the visualisation
        kml = Kml()
        fol = kml.newfolder(name="Vessels")

        shared_style = Style()
        shared_style.labelstyle.color = 'ffffffff'  # White
        shared_style.labelstyle.scale = size  
        shared_style.iconstyle.color = 'ffffffff'  # White
        shared_style.iconstyle.scale = scale
        shared_style.iconstyle.icon.href = icon
        shared_style.linestyle.color = 'ff0055ff'  # Red
        shared_style.linestyle.width = width

        nodes = list(env.FG.nodes)
        
        # each timestep will be represented as a single point
        for log_index, value in enumerate(list(env.FG.nodes)[0:-1-1]):

            pnt = fol.newpoint(name='', 
                               coords=[(nx.get_node_attributes(env.FG, "Geometry")[nodes[log_index]].x,
                                        nx.get_node_attributes(env.FG, "Geometry")[nodes[log_index]].y)])
            pnt.style = shared_style

        edges = list(env.FG.edges)
        for log_index, value in enumerate(list(env.FG.edges)[0:-1-1]):

            lne = fol.newlinestring(name='',
                                    coords = [(nx.get_node_attributes(env.FG, "Geometry")[edges[log_index][0]].x,
                                               nx.get_node_attributes(env.FG, "Geometry")[edges[log_index][0]].y),
                                              (nx.get_node_attributes(env.FG, "Geometry")[edges[log_index][1]].x,
                                               nx.get_node_attributes(env.FG, "Geometry")[edges[log_index][1]].y)])
            lne.style = shared_style
                
        kml.save(fname)