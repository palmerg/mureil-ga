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

import numpy as np 

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

    ### MARCELLE's example placeholder
    #demand_growth_mult = {'2010': 1.0, '2020': 1.2, '2030': 1.4, '2040': 1.6, '2050': 1.8}
    #
    # an extremely rough use of the efficiency settings
    #efficiency_mult = 1 - float(settings['residential_efficiency']) / 100
    #
    #return demand_driver['ts_demand'] * demand_growth_mult[year] * efficiency_mult

    ### Steven's translation of Roger's model
    ### Note that the integration here is very rough - the data should come from the Data
    ### object, and the configuration should come from a Demand object (tbd). Actually
    ### all of this should be in a Demand object, when I invent one ...

    # values from Interface
    residential_efficiency = settings['residential_efficiency']
    residential_intelligence_transmission = settings['residential_intelligence_transmission']
    residential_micro_grids = settings['residential_micro_grids']
    residential_medium_scale_distributed = settings['residential_medium_scale_distributed']
    residential_demand_management = settings['residential_demand_management']
    residential_storage = settings['residential_storage']
    commercial_efficiency = settings['commercial_efficiency']
    commercial_building_design = settings['commercial_building_design']
    commercial_process_design = settings['commercial_process_design']
    commercial_cogen_trigen = settings['commercial_cogen_trigen']
    commercial_demand_management = settings['commercial_demand_management']
    commercial_storage = settings['commercial_storage']
    commercial_peak_curtailment = settings['commercial_peak_curtailment']
    grid_efficiency = settings['grid_efficiency']
    grid_house_design_efficiency = settings['grid_house_design_efficiency']
    grid_new_appliance_use = settings['grid_new_appliance_use']
    grid_small_scale_solar_pv = settings['grid_small_scale_solar_pv']
    grid_demand_management = settings['grid_demand_management']
    grid_storage = settings['grid_storage']
    grid_smart_meters = settings['grid_smart_meters']

    # merge together the different factors into 4 different overall effects
    # this need to be refined to be more realistic (one day)
    total_efficiency = residential_efficiency + \
                       commercial_efficiency + \
                       grid_efficiency + \
                       grid_house_design_efficiency + \
                       grid_new_appliance_use

    total_d_reduction = residential_intelligence_transmission + \
                        residential_micro_grids + \
                        residential_medium_scale_distributed + \
                        commercial_cogen_trigen + \
                        grid_small_scale_solar_pv + \
                        commercial_cogen_trigen

    total_design = commercial_building_design + \
                   grid_house_design_efficiency

    total_dsm = residential_demand_management + \
                residential_storage + \
                commercial_storage  + \
                commercial_peak_curtailment + \
                grid_demand_management + \
                grid_storage

    # scale the totals to be out of 1
    total_efficiency =  total_efficiency/500.0
    total_d_reduction = total_d_reduction/600.0
    total_design = total_design/200.0
    total_dsm = total_dsm/600.0

    model_params = {'ambient':17.25, 'weatherpow':1.5, 'wakeup':10,\
                        'sleep':41, 'background':1.5, 'businessfac':1.125,\
                        'weatherfac':0.8, 'resifac':0.875}

    timeseries                 = readindata()
    model_params['weatherfac'] = model_params['weatherfac'] * (1-total_design)
    model, error               = bottom_up(timeseries, model_params, year, 0.5)

    industry    = model['industry']
    residential = model['residential']
    commercial  = model['commercial']

    # DEMAND SHAPING
    shapediff = demandshape(timeseries['time'], model, 0.5, 20*total_dsm)
    # EFFICIENCY
    industry   = industry   - 1.0 * total_efficiency
    commercial = commercial - 1.0 * total_efficiency
    # DEMAND REDUCTION
    model_pred = industry + residential + commercial - \
                 shapediff - 1.0*total_d_reduction

    # MG - The data for the rest of the sim is in hours, but the source data for
    # this bit is in half-hours. Just drop out half of it.
    
    # and multiply by 1000 as this is GW and we expect MW
    if (timestep_hrs == 1):
        result = model_pred[0::2] * 1000
    else:
        result = model_pred * 1000
        
    return result


def readindata():
    import os
    this_dir = os.path.dirname(os.path.realpath(__file__))
    file_DOW         = open(this_dir + '/DAYOFWEEK.txt','r')
    file_demand      = open(this_dir + '/DEMAND_IN.txt','r')
    file_temperature = open(this_dir + '/TEMPERATURE.txt','r')

    temp_DOW         = file_DOW.readlines()
    temp_demand      = file_demand.readlines()
    temp_temperature = file_temperature.readlines()

    ti = [float(line.split()[0].strip()) for line in temp_DOW]
    do = [line.split()[1].strip()        for line in temp_DOW]
    de = [float(line.split()[1].strip()) for line in temp_demand]
    te = [float(line.split()[1].strip()) for line in temp_temperature]

    file_DOW.close()
    file_demand.close()
    file_temperature.close()

    timeseries = {'time':np.array(ti),'dow':np.array(do),\
              'demand':np.array(de),'temperature':np.array(te)}

    return timeseries


def bottom_up(timeseries, params_dict, year, timestep):

    #increases in demand in 2010,2020,2030,2040,2050
    runyear_fac = {'2010':1.0,'2020':1.2,'2030':1.4,'2040':1.6,'2050':1.8}

    ambient     = params_dict['ambient']
    weatherpow  = params_dict['weatherpow']
    wakeup      = params_dict['wakeup']
    sleep       = params_dict['sleep']
    background  = params_dict['background']
    businessfac = params_dict['businessfac']
    weatherfac  = params_dict['weatherfac']
    resifac     = params_dict['resifac']

    time        = timeseries['time']
    dow         = timeseries['dow']
    demand      = timeseries['demand']
    temperature = timeseries['temperature']

    error       = 0.0
    t_step      = int(24/timestep)
    industry    = [2.94 for i in demand]
    industry    = np.array(industry)

    awake = np.zeros(t_step)
    for i in range(t_step):
        if i < wakeup:
            awake[i] = 0.1
        elif i < (wakeup+(3/timestep)):
            awake[i] = 0.1 + (i-wakeup)*0.15
        elif i < sleep:
            awake[i] = 1.0
        else:
            awake[i] = 1.0 - (i-sleep)*0.075

    if awake[-1] > 0.1:     # continue ramp down into the next morning
        isteps = int((awake[-1]-0.1)/0.075)
        for i in range(isteps+1): awake[i] = awake[i-1]-0.075

    business = np.zeros(t_step)
    b_open   = int(8/timestep)
    b_close  = int(16/timestep)
    for i in range(t_step):
        if i < b_open:
            business[i] = 0.1
        elif i < (b_open+(3/timestep)):
            business[i] = 0.1 + (i-b_open)*0.15
        elif i < b_close:
            business[i] = 1.0
        elif i < (b_close+(3/timestep)):
            business[i] = 1.0 - (i-b_close)*0.15
        else:
            business[i] = 0.1

    ndays        = int(len(demand)/t_step)
    awake_rep    = np.array([i for n in range(ndays) for i in awake])
    business_rep = np.array([i for n in range(ndays) for i in business])
    business_rep = np.where(dow == 'E', np.ones(len(business_rep))*0.1, business_rep)
    
    tdiff        = ambient - temperature
    teffect      = (abs(tdiff)/10)**weatherpow

    commercial   = background/2 + business_rep*businessfac + teffect*weatherfac/2
    residential  = background/2 + awake_rep*resifac        + teffect*weatherfac/2

    industry     = industry    * runyear_fac[year]
    residential  = residential * runyear_fac[year]
    commercial   = commercial  * runyear_fac[year]

    model        = {'industry':industry,'residential':residential,\
                    'commercial': commercial}
    model_pred   = industry + residential + commercial

    error = error + sum(abs(demand/1000.0 - model_pred))\
        + abs(5000 - 5000*sum(commercial)/sum(residential))

    return model, error


def demandshape(time, model, timestep, target):

    demand = model['industry'] + model['residential'] + model['commercial']
    shapediff = np.zeros(time.shape)
    t_step    = int(24/timestep)
    ndays     = len(demand)/t_step

    for id in range(ndays):
        daydemand = demand[id*t_step:id*t_step+t_step].copy()

        # check the maximum available for load shaping

        demandmean  = sum(daydemand)/float(t_step)
        mean_filter = daydemand > demandmean
        totavail    = sum(daydemand[mean_filter] - demandmean)
        newtarget   = min(target, totavail)
        newdemand   = daydemand.copy()
        peak        = max(daydemand)
        mini        = min(daydemand)

        GWhsaved    = 0.0
        counter     = 1
        while GWhsaved <= newtarget:
            yval                  = peak - 0.1*counter
            GWh_filter            = daydemand > yval
            GWhsaved              = sum(daydemand[GWh_filter] - yval)
            newdemand[GWh_filter] = yval
            counter += 1

        counter   = 1
        GWhearned = 0.0
        while GWhearned <= GWhsaved:
            yval                  = mini + 0.1*counter
            GWh_filter            = daydemand < yval
            GWhearned             = sum(yval - daydemand[GWh_filter])
            newdemand[GWh_filter] = yval
            counter += 1
        
        shapediff[id*t_step:id*t_step+t_step] = daydemand-newdemand

    return shapediff

    