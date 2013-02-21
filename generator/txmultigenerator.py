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

"""Module with base class for generator objects that can work in a multi-timeperiod
system, and which fit in with a transmission model and economic model.

Note that the code implemented here is a simple unoptimised implementation. You
may wish to override many of the classes here for your type of generator.
"""

from tools import configurablebase, mureilexception
import copy
import numpy

class TxMultiGeneratorBase(configurablebase.ConfigurableMultiBase):
    """The base class for generic generators that work in a multi-timeperiod
    system and can work with a transmission model and economic model.
    """
    
    def __init__(self):
        """Do very basic initialisation of class members.
        Valid operation does not occur until all of the 'set'
        functions below, and set_config(), have been called.
        """
        
        configurablebase.ConfigurableMultiBase.__init__(self)
        self.data = {}
        self.starting_state = {
            'curr_period': None,
            # capacity is a dict of tuples, with keys of the site index,
            # containing ([capacity], [build], [decomm]) where the
            # lists are all the same length, identifying the capacity
            # at the site, when it was built (start of period), and when it will be 
            # decommissioned (end of period). Each list is of type numpy.array.
            'capacity': {}
        }

        # params_to_site maps the index in the params list to the site indices.
        self.params_to_site = []
        

    def get_details(self):
        """Return a list of flags indicating the properties of the generator.
        """
        flags = {}
        flags['dispatchable'] = False
        flags['technology'] = 'generic'
        # 'model_type' is one of 'generator', 'demand_source',
        # 'demand_management', 'missed_supply'
        flags['model_type'] = 'generator'
        
        return flags
        

    def get_starting_state_handle(self):
        """Return the starting state, in whatever form the model chooses, to be
        passed in at each iteration by the master. The deepcopy ensures it is 
        thread-safe as a separate copy is used for each master calculate call.
        
        Outputs:
            starting_state_handle: a new copy of the starting state of this model
        """
        
        return copy.deepcopy(self.starting_state)
    
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            period_list: the list of ids for each time period, typically taken from the
                global period_list.
            time_scale_up_mult: float - the value to multiply non-discounted items,
                such as carbon emissions, by to account for a shorter dataset than the
                calculation period length.
            variable_cost_mult: as for time_scale_up_mult, but may include a factor for
                cost discounting.
            carbon_price_m: float - carbon price in $M/tonne
        """
        return configurablebase.ConfigurableMultiBase.get_config_spec(self) + [
            ('variable_cost_mult', float, 1.0),
            ('time_scale_up_mult', float, 1.0),
            ('carbon_price_m', float, 0.0),
            ('startup_data_name', None, ''),
            ('decommissioning_cost', float, 0),
            ('capital_cost', float, None),
            ('params_to_site_data_name', None, ''),
            ('time_period_yrs', int, None),
            ('lifetime', int, None),
            ('size', float, 1.0)
            ]


    def complete_configuration_pre_expand(self):
        """Complete the configuration prior to expanding the
        period configs. 
        
        This implementation checks that the lifetime is a multiple
        of time_period_yrs.
        """
        
        time_period_yrs = self.config['time_period_yrs']
        lifetime = self.config['lifetime']
        error = None
        if isinstance(lifetime, dict):
            for value in lifetime.itervalues():
                if not ((value % time_period_yrs) == 0):
                    error = value
        else:
            if not ((lifetime % time_period_yrs) == 0):
                error = lifetime
        
        if error is not None:
            msg = ('In section ' + self.config['section'] + ', lifetime = ' +
                str(error) + ' which is required to be a multiple of time_period_yrs of ' +
                str(time_period_yrs))
            raise mureilexception.ConfigException(msg, {})
                

    def get_data_types(self):
        """Return a list of keys for each type of
        data required, for example ts_wind, ts_demand.
        
        Outputs:
            data_type: list of strings - each a key name 
                describing the data required for this generator.
        """
        
        data_types = []
        
        if len(self.config['startup_data_name']) > 0:
            data_types.append(self.config['startup_data_name'])

        if len(self.config['params_to_site_data_name']) > 0:
            data_types.append(self.config['params_to_site_data_name'])
        
        return data_types
        
        
    def set_data(self, data):
        """Set the data dict with the data series required
        for the generator.
        
        Inputs:
            data: dict - with keys matching those requested by
                get_data_types. 
        """
        if len(self.config['startup_data_name']) > 0:
            startup_data = data[self.config['startup_data_name']]
            # Expect the startup_data to be an array of generators * 4
            # Where the first element of each row is site index, 
            # second is capacity, 
            # third is build date, 
            # fourth is decommissioning date.

            # Find out which build periods are covered.
            self.extra_periods = map(int, (list(set(startup_data[:,2]))))
            self.extra_periods.sort()

            # And insert each existing generator into the starting state.
            cap_list = self.starting_state['capacity']

            for i in range(startup_data.shape[0]):
                site_index = int(startup_data[i, 0])
                new_cap = startup_data[i, 1]
                period = int(startup_data[i, 2])
                decomm_date = int(startup_data[i, 3])
                
                if site_index not in cap_list:
                    cap_list[site_index] = (numpy.array([new_cap], dtype=float), 
                        numpy.array([period], dtype=int), 
                        numpy.array([decomm_date], dtype=int))
                else:
                    old_cap, old_period, old_decomm_date = cap_list[site_index]
                    cap_list[site_index] = (numpy.append(old_cap, new_cap), 
                        numpy.append(old_period, period),
                        numpy.append(old_decomm_date, decomm_date))

        params_to_site_name = self.config['params_to_site_data_name']
        if len(params_to_site_name) > 0:
            self.params_to_site = data[params_to_site_name]

        
    def get_param_count(self):
        """Return the number of parameters that this generator,
        as configured, requires to be optimised, per time period.
        
        Outputs:
            param_count: non-negative integer - the number of
                parameters required per time period.
        """
        return len(self.params_to_site)
        
    
    def get_param_starts(self):
        """Return two lists - one for min, one max, for starting values for the
        params. Must be either empty or the same length as param_count.
        
        Outputs:
            min_start_list: list of param integers, or []
            max_start_list: list of param integers, or []
        """
    
        return [], []
        
        
    def update_state_new_period_list(self, state_handle, period, new_capacity):
        """Update the 'state_handle' object, in place, with the new_capacity, which will
        list the new capacity built at that date, the location it is built, and the
        decommissioning date.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model before the current time period
            new_capacity: a list of tuples of (site_index, new_capacity, decommissioning_date)
            period: an integer identifying the period - e.g. 2010, 2020.
            
        Outputs:
            None, but the 'state_handle' input is modified in-place to now represent the state after this
            increment.
        """

        state_handle['curr_period'] = period

        cap_list = state_handle['capacity']        

        for site_index, new_cap, decomm_date in new_capacity:
            site_index = int(site_index)
            decomm_date = int(decomm_date)
            if site_index not in cap_list:
                cap_list[site_index] = (numpy.array([new_cap], dtype=float), 
                    numpy.array([period], dtype=int), 
                    numpy.array([decomm_date], dtype=int))
            else:
                old_cap, old_period, old_decomm_date = cap_list[site_index]
                cap_list[site_index] = (numpy.append(old_cap, new_cap), 
                    numpy.append(old_period, period),
                    numpy.append(old_decomm_date, decomm_date))

        return None


    def update_state_new_period_params(self, state_handle, period, new_params):
        """Update the 'state_handle' object, in place, with the new_params. Typically this would
        calculate the capacity (or other values) as dictated by the new_params, and
        add these to the state. 
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model before the current time period
            new_params: a numpy.array list of param numbers of length matching self.get_param_count
            period: an integer identifying the period - e.g. 2010, 2020.
            
        Outputs:
            None, but the 'state_handle' input is modified in-place to now represent the state after this
            increment.
        """
            
        state_handle['curr_period'] = period
        curr_conf = self.period_configs[period]
        decomm_date = curr_conf['lifetime'] - curr_conf['time_period_yrs'] + period
        
        cap_list = state_handle['capacity']        

        new_cap = new_params * curr_conf['size']

        for i in (numpy.nonzero(new_cap)[0]):
            site_index = self.params_to_site[i]

            if site_index not in cap_list:
                cap_list[site_index] = (numpy.array([new_cap[i]], dtype=float), 
                    numpy.array([period], dtype=int), 
                    numpy.array([decomm_date], dtype=int))
            else:
                old_cap, old_period, old_decomm_date = cap_list[site_index]
                cap_list[site_index] = (numpy.append(old_cap, new_cap[i]), 
                    numpy.append(old_period, period),
                    numpy.append(old_decomm_date, decomm_date))

        return None
 
    
    def calculate_update_decommission(self, state_handle):
        """Update the 'state_handle' object, in place, after decommissioning plants at the
        end of the current period. Calculate the cost of the decommissioning.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model after building new capacity in
                the current time period
            
        Outputs:
            total_cost: the total decommissioning cost across all sites.
            decommissioned: a list of tuples of (site_index, capacity, cost), describing the
                capacity decommissioned at the end of this period, and the cost of the 
                decommissioning.
            
            The 'state_handle' input is modified in-place to now represent the state after this
            increment.
        """
        
        period = state_handle['curr_period']
        cap_list = state_handle['capacity']
    
        total_cost = 0.0
        sites = []
        cost = []
        decommissioned = []
        fully_decommissioned = []
    
        decomm_cost = self.period_configs[period]['decommissioning_cost']
    
        for site, value in cap_list.iteritems():
            (cap, build, decomm_dates) = value
            decomm = numpy.nonzero(decomm_dates == period)[0]
            if len(decomm) > 0:
                sites.append(site)
                decom_cap = sum(cap[decomm])
                decommissioned.append(decom_cap)
                this_cost = decom_cap * decomm_cost
                cost.append(this_cost)
                total_cost += this_cost
                
                # if all capacity is gone from this site
                if len(decomm) == len(decomm_dates):
                    fully_decommissioned.append(site)

                # and delete the entries
                cap_list[site] = (numpy.delete(cap, decomm),
                    numpy.delete(build, decomm),
                    numpy.delete(decomm_dates, decomm))
                
        for site in fully_decommissioned:
            del cap_list[site]
    
        return total_cost, zip(sites, decommissioned, cost)
 
 
    def calculate_new_capacity_cost(self, state_handle):
        """Calculate the capital cost of the infrastructure built in the latest period.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model at the current time period
                
        Outputs:
            total_cost: the sum of the new capacity costs across all sites
            new_capacity: a list of tuples of (site_index, new_capacity, cost), describing the
                capacity added at the start of this period.
        """
        
        period = state_handle['curr_period']
        cap_list = state_handle['capacity']
    
        total_cost = 0.0
        sites = []
        cost = []
        new_capacity = []
        
        for site, value in cap_list.iteritems():
            new_build = numpy.nonzero(value[1] == period)[0]
            if len(new_build) > 0:
                sites.append(site)
                this_cost, new_cap = self.calculate_capital_cost_site(
                    value, period, new_build, site)
                new_capacity.append(new_cap)
                cost.append(this_cost)
                total_cost += this_cost
    
        return total_cost, zip(sites, new_capacity, cost)

 
    def calculate_capital_cost_site(self, site_tuple, period, new_build, site):
        """"Calculate the incremental capital cost incurred in this 
        period by the new capacity, for this site.
        
        This is a useful function for generators to override to implement
        cost functions that depend on the existing installed capacity. The
        implementation here simply multiplies by a capital cost per unit
        of new capacity.
        
        Inputs: 
            site_tuple: a ([capacity], [build], [decom]) tuple from the
                state_handle.
            period: the current period, an integer
            new_build: an index array into the site_tuple lists, indicating
                which are new capacity.
            site: the site index
                
        Outputs:
            cost: the cost in $M of this new capacity
            new_capacity: the total new capacity installed at this site
        """
        
        (capacity, build, decomm) = site_tuple
        
        capacity_cost = self.period_configs[period]['capital_cost']
        new_cap = sum(capacity[new_build])
        this_cost = new_cap * capacity_cost
    
        return this_cost, new_cap        
            
    
    def get_capacity(self, state_handle):
        """Extracts from the 'state_handle' parameter the current total capacity at each active site.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model at the current time period

        Outputs:
            capacity: a list of the installed electrical capacity at each site for the active sites. This list will correspond
                to the list of site indices as returned by get_site_indices with the same state_handle.
        """
        
        index_list = self.get_site_indices(state_handle)
        cap_list = state_handle['capacity']
        
        capacity = []
        
        for site in index_list:
            capacity.append(sum(cap_list[site][0]))
        
        return capacity

    
    def get_site_indices(self, state_handle):
        """Extracts from the 'state_handle' parameter the list of indices corresponding to sites
        with active capacity.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model at the current time period

        Outputs:
            site_indices: a list of identifying indices corresponding to sites with active capacity,
                in ascending order.
        """
        
        site_indices = state_handle['capacity'].keys()
        site_indices.sort()
        
        return site_indices


    def calculate_outputs_and_costs(self, state_handle, supply_request, max_supply=[], price=[]):
        """Calculate the supply output of each site at each point in the timeseries. Return
        a set of timeseries of supply. Also calculate, for the length of time
        represented by the timeseries length, the variable cost (fuel, maintenance etc)
        for each site, and the carbon emissions.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model at the current time period
            supply_request: a timeseries indicating the total requested supply 
                for this generator
            max_supply: optional - a set of timeseries indicating any curtailing
                due to transmission restrictions.
            price: optional - a timeseries indicating the market price in $/MWh
            
        Outputs:
            All lists below will correspond to the list of site indices as returned by 
            get_site_indices with the same state_handle.
            
            supply: a set of timeseries, one per site, indicating output in MW at
                each timepoint in supply_request.
            variable_cost: a set of costs, one per site, in $M, for the timeseries length.
            carbon_emissions: a set of carbon emissions, one per site, in tonnes of CO2,
                for the timeseries length.
            other: an arbitrary dict, for extra information such as reliability.
        """
        
        return [[]], [], [], {}
        
        
    def calculate_time_period_simple(self, state_handle, period, new_params, 
        supply_request, full_results=False):
        """Calculate, for this time period, the total supply of all sites in this model,
        and the total cost. This is for use in a simple dispatch model with copper-plated
        transmission.

        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model before the current time period
            period: an integer identifying the period - e.g. 2010, 2020.
            new_params: a list of param numbers of length matching self.get_param_count
            supply_request: a timeseries indicating the total requested supply 
                for this generator
            full_results: optional - if True, return a detailed results structure in addition

        Outputs:
            site_indices: the identifying indices of each site with active capacity. All lists of
                sites below will correspond with this list.
            cost: the total cost incurred in this period
            supply: the total supply from all active sites in this model

            results: only returned if full_results is True. Returns a dict with items:
                capacity: a list of the installed electrical capacity at each site.
                decommissioned: a list of tuples of (site_index, capacity, cost) - the capacity 
                    at each site that was decommissioned at the end of this period.
                new_capacity: a list of tuples of (site_index, capacity, cost) - the new capacity 
                    built at each site in this period.
                supply: a set of timeseries, one per site, indicating output in MW at
                    each timepoint in supply_request.
                variable_cost_period: a set of costs, one per site, in $M, for the period.
                carbon_emissions_period: a set of carbon emissions, one per site, in tonnes of CO2,
                    for the period, or empty list if none.
                other: an arbitrary dict, for extra information such as reliability.
                desc_string: a descriptive string on the current state and output
        """
    
        curr_config = self.period_configs[period]

        # Update the state and get the calculations for each site
        self.update_state_new_period(state_handle, period, new_params)
        site_indices = self.get_site_indices(state_handle)
        capital_cost, new_capacity = self.calculate_capital_cost(state_handle)
        supply_list, variable_cost_list, carbon_emissions_list, other_list = ( 
            self.calculate_outputs_and_costs(state, supply_request))

        # Compute the total supply
        supply = numpy.sum(supply_list, axis=0)
        
        # Compute the total variable costs, including carbon cost, for the timeseries, scaled up
        cost = (numpy.sum(variable_cost_list, axis=0) + 
            (numpy.sum(carbon_emissions_list, axis=0) * curr_config['carbon_price'] / 1e6) * (
            curr_config['variable_cost_mult']))
                
        # Do the decommissioning
        decomm_cost, decommissioned = self.calculate_update_decommission(state_handle)

        # Add the capital and decommissioning costs
        cost += decomm_cost
        cost += capital_cost

        if not full_results:
            return site_indices, cost, supply

        if full_results:
            results = {}
            results['sites'] = site_indices
            results['capacity'] = self.get_capacity(state_handle)
            results['decommissioned'] = decommissioned
            results['new_capacity'] = new_capacity
            results['supply'] = supply_list
            results['variable_cost_period'] = variable_cost_list * curr_config['variable_cost_mult']
            results['carbon_emissions_period'] = (carbon_emissions_list * 
                curr_config['time_scale_up_mult'])
            results['other'] = other_list
            results['desc_string'] = self.get_simple_desc_string(results, state_handle)


    def get_simple_desc_string(self, results, state_handle):
        """Given the results dict as created by calculate_time_period_simple, prepare
        a descriptive string for printed output.
        
        Inputs:
            results: a results dict as output by calculate_time_period_simple.
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model at the current time period

        Outputs:
            desc_string: a descriptive string suitable for human reading.
        """
        
        return "Generator, not further described"

 
    def calculate_time_period_full(self, state_handle, period, new_params, supply_request, 
        max_supply=[], price=[], make_string=False, do_decommissioning=True):
        """Calculate, for this time period, the supply from each site, the capacity at
        each site, the variable cost, capital cost and carbon emissions. Expose all of 
        the parameters and require the transmission and/or economic models to do the
        rest of the work.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model before the current time period
            period: an integer identifying the period - e.g. 2010, 2020.
            new_params: a list of param numbers of length matching self.get_param_count
            supply_request: a timeseries indicating the total requested supply 
                for this generator
            max_supply: optional - a set of timeseries indicating any curtailing
                due to transmission restrictions.
            price: optional - a timeseries indicating the market price in $/MWh
            make_string: if True, return as the final output, a string describing the
                current state and outputs.
            do_decommissioning: if True, update to the state after decommissioning at the
                end of the period. Set to False if recalculate_time_period_full will be called.
            
        Outputs:
            results: a dict with all of the following values
                site_indices: the identifying indices of each site with active capacity. All lists of
                    sites below will correspond with this list.
                capacity: a list of the installed electrical capacity at each site.
                decommissioned: a list of tuples of (site_index, capacity, cost) - the capacity 
                    at each site that was decommissioned at the end of this period.
                new_capacity: a list of tuples of (site_index, capacity, cost) - the new capacity 
                    built at each site in this period.
                supply: a set of timeseries, one per site, indicating output in MW at
                    each timepoint in supply_request.
                variable_cost_ts: a set of costs, one per site, in $M, for the timeseries length.
                carbon_emissions_ts: a set of carbon emissions, one per site, in tonnes of CO2,
                    for the timeseries length, or empty list if none.
                other: an arbitrary dict, for extra information such as reliability.
                desc_string: a descriptive string on the current state and output, 
                    only returned if make_string in inputs is True.
        """
        
        results = {}
        self.update_state_new_period(state_handle, period, new_params)
        results['site_indices'] = self.get_site_indices(state_handle)
        results['capacity'] = self.get_capacity(state_handle)
        dummy, results['new_capacity'] = self.calculate_capital_cost(state_handle)
        results['supply'], results['variable_cost_ts'], results['carbon_emissions_ts'], results['other'] = (
            self.calculate_outputs_and_costs(state_handle, supply_request, max_supply, price))
        if do_decommissioning:
            dummy, results['decommissioned'] = (
                self.calculate_update_decommissioning(state_handle))
        else:
            results['decommissioned'] = []

        if make_string:
            results['desc_string'] = self.get_full_desc_string(results, state_handle)
            return results


    def recalculate_time_period_full(self, state_handle, results, supply_request, max_supply=[], price=[], make_string=False):
        """Recalculate as for calculate_time_period_full, but without updating the state first.
        Typically this would be used when iterating through a transmission model.

        calculate_time_period_full must be called first, with do_decommissioning set to False. Once the
        iterations are complete, calculate_update_decommissioning must be called to complete the 
        calculations for the period.

        This implementation below assumes that the decommissioning and capital costs are not dependent on
        supply_request, max_supply or price.
        
        Inputs:
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model at the current time period.
            results: the dict output from a run of calculate_time_period_full.
            supply_request, max_supply, price, make_string: as for calculate_time_period_full.
            
        Outputs:
            None - but the results input is updated in-place.
        """

        results['supply'], results['variable_cost_ts'], results['carbon_emissions_ts'], results['other'] = (
            self.calculate_outputs_and_costs(state_handle, supply_request, max_supply, price))

        if make_string:
            results['desc_string'] = self.get_full_desc_string(results, state_handle)
            return results
        else:
            return results        


    def get_full_desc_string(self, results, state_handle):
        """Given the results dict as created by calculate_time_period_full, prepare
        a descriptive string for printed output.
        
        Inputs:
            results: a results dict as output by calculate_time_period_full.
            state_handle: an arbitrary object, which initiated from self.get_starting_state_handle, 
                that describes the state of the generator model at the current time period

        Outputs:
            desc_string: a descriptive string suitable for human reading.
        """
        
        return "Generator, not further described"
