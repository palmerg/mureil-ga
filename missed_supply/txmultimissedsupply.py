#
#
# Copyright (C) University of Melbourne 2013
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

"""Module for a missed-supply model using the TxMultiGeneratorBase base class.
"""

from tools import configurablebase
from generator import txmultigeneratorbase
import numpy


class TxMultiLinearMissedSupply(txmultigeneratorbase.TxMultiGeneratorBase):
    """Missed supply model charging a flat price per MWh missed.
    """

    def get_details(self):
        """Return a list of flags indicating the properties of the generator,
        as defined in TxMultiGeneratorBase.
        """
        flags = txmultigeneratorbase.TxMultiGeneratorBase.get_details(self)
        flags['dispatchable'] = True
        flags['model_type'] = 'missed_supply'
        
        return flags
        

    def get_site_indices(self, state_handle):
        """Implement get_site_indices as defined in TxMultiGeneratorBase. 
        
        Here a dummy 'site' of -1 is returned as the missed supply modelled here
        doesn't have a site.
        """
        return [-1]


    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            as for txmultigenerator.TxMultiGeneratorBase, plus:

        cost_per_mwh: float - the cost in $ per MWh of missed supply
        timestep_hrs: float - the system timestep in hours
        variable_cost_mult: float - the value to multiply by to account for a shorter
            dataset than the calculation period length. It may include a factor for
            cost discounting.

        """
        
        spec = txmultigeneratorbase.TxMultiGeneratorBase.get_config_spec(self) + [
            ('cost_per_mwh', float, None),
            ('timestep_hrs', float, None),
            ('variable_cost_mult', float, None),
            ('time_scale_up_mult', float, None)
            ]
        
        return spec


    def calculate_outputs_and_costs(self, state_handle, supply_request, max_supply=[], price=[]):
        """Implement calculate_outputs_and_costs as defined in TxMultiGeneratorBase.
        
        This model charges a fixed price per mwh of missed supply, which is any positive values
        in supply_request.
        """
        
        this_conf = self.period_configs[state_handle['curr_period']]
        
        cap_list = state_handle['capacity']
        site_indices = self.get_site_indices(state_handle)
        num_sites = len(site_indices)
        supply = numpy.zeros((num_sites, len(supply_request)))
        vble_cost = numpy.zeros(num_sites)
        carbon = numpy.zeros(num_sites)
        
        # The missed supply model implemented here only makes sense as a single 'site'.
        site = site_indices[0]
        supply[0,:] = supply_request.clip(0)
        sum_out = numpy.sum(supply[0,:])
        missed_mwh = sum_out * this_conf['timestep_hrs']

        # cost is in $M but cost_per_mwh is $
        vble_cost[0] = (1e-6 * missed_mwh * this_conf['cost_per_mwh'])
        
        return supply, vble_cost, carbon, {'total_missed': missed_mwh}
        

    def calculate_time_period_simple(self, state_handle, period, new_params, 
        supply_request, full_results=False):
        """Implement calculate_time_period_simple as defined in TxMultiGeneratorBase for
        the missed_supply model.
        
        This missed-supply model does not handle any concept of capacity or site so returns
        empty lists for most things, and -1 for the site.
        """
    
        curr_config = self.period_configs[period]
        state_handle['curr_period'] = period

        # Update the state and get the calculations for each site
        supply_list, variable_cost_list, dummy, other_list = ( 
            self.calculate_outputs_and_costs(state_handle, supply_request))
        supply = supply_list[0,:]

        # Compute the total variable costs - carbon emissions are zero for missed supply
        cost = variable_cost_list[0] * curr_config['variable_cost_mult']
                
        if not full_results:
            return [-1], cost, supply

        if full_results:
            results = {}
            results['site_indices'] = [-1]
            results['cost'] = cost
            results['aggregate_supply'] = supply
            results['capacity'] = [0]
            results['decommissioned'] = []
            results['new_capacity'] = []
            results['supply'] = supply_list
            results['variable_cost_period'] = variable_cost_list * curr_config['variable_cost_mult']
            results['carbon_emissions_period'] = 0
            results['total_supply_period'] = (curr_config['time_scale_up_mult'] * numpy.sum(supply) *
                curr_config['timestep_hrs'])
            results['other'] = other_list
            results['desc_string'] = self.get_simple_desc_string(results, state_handle)

        return [-1], cost, supply, results
    

    def calculate_time_period_full(self, state_handle, period, new_params, supply_request, 
        max_supply=[], price=[], make_string=False, do_decommissioning=True):
        """Implement calculate_time_period_full as defined in TxMultiGeneratorBase for
        the missed_supply model.
        
        This missed-supply model does not handle any concept of capacity or site so returns
        empty lists for most things, and -1 for the site.
        """
        
        state_handle['curr_period'] = period
        results = {}
        results['supply'], results['variable_cost_ts'], results['carbon_emissions_ts'], results['other'] = (
            self.calculate_outputs_and_costs(state_handle, supply_request, max_supply, price))

        results['decommissioned'] = []
        results['site_indices'] = [-1]
        results['capacity'] = [0]
        results['new_capacity'] = []
        
        if make_string:
            results['desc_string'] = self.get_full_desc_string(results, state_handle)
            return results


    def get_simple_desc_string(self, results, state_handle):
        """Implement get_simple_desc_string as defined in TxMultiGeneratorBase.
        """
        return 'Linear Missed-Supply, total {:.2f} MW-timestamps missed'.format(
            results['other']['total_missed'])

        
    def get_full_desc_string(self, results, state_handle):
        """Implement get_full_desc_string as defined in TxMultiGeneratorBase.
        """
        return self.get_simple_desc_string(results, state_handle)
