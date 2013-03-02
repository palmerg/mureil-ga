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

"""Module for a variable generator using the txmultigeneratormultisite base class.
"""

from tools import configurablebase, mureilexception
from generator import txmultigeneratormultisite
import copy
import numpy
import string

class TxMultiVariableGeneratorBase(txmultigeneratormultisite.TxMultiGeneratorMultiSite):
    """A simple implementation of a variable generator, providing 
    per-unit capital costs.
    """

    def get_details(self):
        """Return a list of flags indicating the properties of the generator.
        """
        flags = txmultigeneratormultisite.TxMultiGeneratorMultiSite.get_details(self)
        flags['technology'] = self.config['tech_type']
        
        return flags
        

    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            as for txmultigenerator.TxMultiGeneratorBase, plus:
            
        tech_type: string - the generic technology type, to report in get_details() as technology.
        detail_type: string - a specific name, e.g. 'onshore_wind_vic', for printing in an output string
        data_name: string - the name of the data array holding the timeseries capacity factor data, e.g. ts_wind. 
        data_map_name: string - the name of the data array e.g. ts_wind_map which holds an n x 2 array
            where n is the number of site indices mapped. The first in each pair is the site index and the second
            the index into the data table. If this is not provided, a 1:1 is assumed.
        data_ts_length: the length of the data timeseries, typically provided globally.
        """
        return txmultigeneratormultisite.TxMultiGeneratorMultiSite.get_config_spec(self) + [
            ('tech_type', None, 'generic_variable'),
            ('detail_type', None, 'generic_variable'),
            ('data_name', None, None),
            ('data_map_name', None, ''),
            ('data_ts_length', int, None)
            ]


    def get_data_types(self):
        """Return a list of keys for each type of
        data required, for example ts_wind, ts_demand.
        
        Outputs:
            data_type: list of strings - each a key name 
                describing the data required for this generator.
        """
        
        data_types = txmultigeneratormultisite.TxMultiGeneratorMultiSite.get_data_types(self)
        
        data_types.append(self.config['data_name'])
        
        if len(self.config['data_map_name']) > 0:
            data_types.append(self.config['data_map_name'])
        
        return data_types
        
        
    def set_data(self, data):
        """Set the data dict with the data series required
        for the generator.
        
        Inputs:
            data: dict - with keys matching those requested by
                get_data_types. 
        """

        txmultigeneratormultisite.TxMultiGeneratorMultiSite.set_data(self, data)

        self.data = data[self.config['data_name']]
        self.site_to_data = {}
        
        if len(self.config['data_map_name']) > 0:
            map_data = data[self.config['data_map_name']]
            for i in range(0, map_data.shape[0]):
                self.site_to_data[map_data[i, 0]] = map_data[i, 1]
            if len(self.params_to_site) == 0:
                # We have a data map, but no params to site, so assume
                # all data are used and map 1:1 to this.
                self.params_to_site = map_data[:,0]

        elif len(self.params_to_site) > 0:
            # No data map is provided, but params_to_site is. If the 
            # lengths agree, map the site index list to the data 1:1.
            
            if not (len(self.params_to_site) == self.data.shape[1]):
                raise mureilexception.ConfigException('In model ' + self.config['section'] +
                    ', no data map is provided, the data is width ' + str(self.data.shape[1]) + 
                    ' and the provided params_to_site list is ' + str(len(self.params_to_site)) +
                    ' so no automatic mapping is possible.', {})
                    
            for i in range(len(self.params_to_site)):
                self.site_to_data[self.params_to_site[i]] = i
        
        else:
            # No list of sites is provided. Just map to ordinal numbers.
            self.params_to_site = range(self.data.shape[1])
            for i in range(0, self.data.shape[1]):
                self.site_to_data[i] = i

        # Check that all of the values in site_to_data are within the
        # self.data matrix.
        
        max_data = self.data.shape[1]
        for data_index in self.site_to_data.itervalues():
            if (data_index < 0) or (data_index >= max_data):
                raise mureilexception.ConfigException('data_index ' + str(data_index) +
                    ' was requested by the model in section ' + self.config['section'] +
                    ' but the maximum index in the data array is ' + str(max_data), {})

        
    def calculate_outputs_and_costs(self, state_handle, supply_request, max_supply=[], price=[]):
        """Implement calculate_outputs_and_costs as defined in TxMultiGeneratorBase, for the
        variable generators.
        """
        
        cap_list = state_handle['capacity']
        site_indices = self.get_site_indices(state_handle)
        num_sites = len(site_indices)
        supply = numpy.zeros((num_sites, len(supply_request)))
        vble_cost = numpy.zeros(num_sites)
        carbon = numpy.zeros(num_sites)
        
        for i in range(num_sites):
            site = site_indices[i]
            total_cap = sum([tup[0] for tup in cap_list[site]])
            data_index = self.site_to_data[site]
            ### TODO - it may be expensive to have self.data this way -
            ### would it help to transpose it when it's read in, so
            ### the memory lines up better?
            supply[i,:] = self.data[:,data_index] * total_cap
        
        return supply, vble_cost, carbon, {}
        

    def get_simple_desc_string(self, results, state_handle):
        """Implement get_simple_desc_string as defined in TxMultiGeneratorBase, for the
        variable generator.
        """

        return self.config['detail_type'] + ' with site capacities (MW): ' + (
            string.join(map('({:d}: {:.2f}) '.format, results['site_indices'], 
            results['capacity'])))
        
        
    def get_full_desc_string(self, results, state_handle):
        """Implement get_full_desc_string as defined in TxMultiGeneratorBase, for the
        variable generator.
        """
        
        return self.get_simple_desc_string(results, state_handle)


class TxMultiVariableGeneratorLinearInstall(TxMultiVariableGeneratorBase):
    """A simple implementation of a variable generator, providing 
    per-unit capital costs plus an install factor if the site is empty.
    """

    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            as for TxMultiVariableGeneratorBase, plus:
            
        install_cost: float, in $M per site - the cost to start up a site where no capacity exists.
        """
        return TxMultiVariableGeneratorBase.get_config_spec(self) + [
            ('install_cost', float, None)
            ]


    def calculate_capital_cost_site(self, site_data, period, site):
        """Implement calculate_capital_cost_site, as defined by TxMultiGeneratorBase.
        
        Calculate the incremental capital cost incurred in this 
        period by the new capacity, for this site.
        
        This function charges a per-MW cost plus an install figure if all
        the current capacity is new, and the site has not been used before
        for this type of generator.
        
        Inputs: 
            site_data: a pair of lists - (current_capacity, history), each 
                a list of tuples of (capacity, build, decom) from the
                state_handle.
            period: the current period, an integer
            site: the site index
                
        Outputs:
            cost: the cost in $M of this new capacity
            new_capacity: the total new capacity installed at this site
        """
        
        new_cap_list = [tup[0] for tup in site_data[0] if (tup[1] == period)]

        capacity_cost = self.period_configs[period]['capital_cost']
        this_cost = sum(new_cap_list) * capacity_cost

        if len(new_cap_list) == len(site_data[0]):
            # check if the site has been used before, ever
            if len(site_data[1]) == 0:
                # the site is new, so charge the 'install' as well
                this_cost += self.period_configs[period]['install_cost']
    
        return this_cost, sum(new_cap_list)        
            
    

