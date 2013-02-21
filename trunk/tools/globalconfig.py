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
# Functions to calculate and process global variables
#

from tools import mureilbuilder, mureilexception

def get_global_spec():
    """Get the spec for global variables that need conversion prior
    to calculating with them. All of these are considered
    optional.
    """
    return [('timestep_mins', float, None),
        ('time_period_yrs', int, None),
        ('timestep_hrs', float, None),
        ('min_param_val', float, None),
        ('max_param_val', float, None),
        ('time_scale_up_mult', float, None),
        ('variable_cost_mult', float, None),
        ('data_ts_length', int, None),
        ('carbon_price', float, None)
        ]
        

def pre_data_global_calcs(global_conf):
    """Update global_conf in place with timestep conversions.
    """
    mureilbuilder.apply_conversions(global_conf, get_global_spec())

    if 'timestep_mins' in global_conf:
        if isinstance(global_conf['timestep_mins'], dict):
            msg = 'Global timestep_mins is required to have the same value across the sim.'
            raise mureilexception.ConfigException(msg, {})
        global_conf['timestep_hrs'] = global_conf['timestep_mins'] / 60
    elif 'timestep_hrs' in global_conf:
        if isinstance(global_conf['timestep_hrs'], dict):
            msg = 'Global timestep_hrs is required to have the same value across the sim.'
            raise mureilexception.ConfigException(msg, {})
        global_conf['timestep_mins'] = global_conf['timestep_hrs'] * 60
        
    # Compute the carbon price in $M/tonne
    if 'carbon_price' in global_conf:
        if isinstance(global_conf['carbon_price'], dict):
            global_conf['carbon_price_m'] = {}
            for period, value in global_conf['carbon_price'].iteritems():
                global_conf['carbon_price_m'][period] = global_conf['carbon_price'][period] / 1e6
        else:
            global_conf['carbon_price_m'] = global_conf['carbon_price'] / 1e6


def post_data_global_calcs(global_conf):
    """Update global_conf now that data length is known. Compute the variable_cost_mult parameter.
    """

    # time_scale_up_mult extrapolates calculations from a dataset along the full time period.
    if 'time_scale_up_mult' not in global_conf:
        if 'time_period_yrs' in global_conf and 'timestep_hrs' in global_conf:
            if isinstance(global_conf['time_period_yrs'], dict):
                msg = 'Global time_period_yrs is required to have the same value across the sim.'
                raise mureilexception.ConfigException(msg, {})

            if isinstance(global_conf['timestep_hrs'], dict):
                msg = 'Global timestep_hrs is required to have the same value across the sim.'
                raise mureilexception.ConfigException(msg, {})
            
            if 'data_ts_length' not in global_conf:
                msg = 'Global calculations of time_scale_up_mult require the data_ts_length parameter to be set'
                raise mureilexception.ConfigException(msg, {})
            
            yrs_of_data = ((global_conf['timestep_hrs'] * float(global_conf['data_ts_length'])) /
                (365.25 * 24))
            global_conf['time_scale_up_mult'] = (float(global_conf['time_period_yrs']) /
                yrs_of_data)

    # Need to know the data length to compute variable_cost_mult - to extrapolate the variable
    # cost along the whole time period being modelled. Some NPV discounting could also be
    # incorporated with a discount rate parameter, when implemented.
    # TODO - add a discounting effect here.
    if 'time_scale_up_mult' in global_conf:
        if 'variable_cost_mult' not in global_conf:
            global_conf['variable_cost_mult'] = global_conf['time_scale_up_mult']


