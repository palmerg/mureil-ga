#
#
# Copyright (C) University of Melbourne 2012
#
#
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#
#

import numpy 

def calculate_demand(demand_driver, settings, year, timestep_hrs):
    """Calculate demand from a modelling approach.
    
    Inputs:
        demand_driver: a dict of numpy timeseries of interest to the model. 
            This example just expects ts_demand, and multiplies it 
            up by a year-based factor.
        settings: a dict of arbitrary settings
        year: the year as a string e.g. '2010'
        timestep_hrs: the size, in hours, of each data point
    
    Outputs:
        demand: a numpy timeseries in MW-timesteps (e.g. in MWh if the timestep
            is hours)
    """

    demand_growth_mult = {'2010': 1.0, '2020': 1.2, '2030': 1.4, '2040': 1.6, '2050': 1.8}

    # an extremely rough use of the efficiency settings
    efficiency_mult = 1 - float(settings['residential_efficiency']) / 100
    
    return demand_driver['ts_demand'] * demand_growth_mult[year] * efficiency_mult
    