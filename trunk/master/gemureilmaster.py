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
import time
import logging
import copy
import json
from os import path

from tools import mureilbuilder, mureilexception, mureiloutput, globalconfig
from tools import configurablebase, mureilbase
from generator import singlepassgenerator

logger = logging.getLogger(__name__)

class GeMureilMaster(mureilbase.MasterInterface, configurablebase.ConfigurableBase):
    def get_full_config(self):
        if not self.is_configured:
            return None
        
        # Will return configs collected from all objects, assembled into full_config.
        full_conf = {}
        full_conf['Master'] = self.config
        full_conf[self.config['data']] = self.data.get_config()
        full_conf[self.config['global']] = self.global_config

        for gen_type in self.dispatch_order:
            gen = getattr(self, gen_type)
            full_conf[self.config[gen_type]] = gen.get_config()

        return full_conf

     
    def set_config(self, full_config, extra_data):
    
        # Master explicitly does not copy in the global variables. It is too confusing
        # to combine those with flags, defaults and values defined in the config files.
        self.load_initial_config(full_config['Master'])
        
        # Get the global variables
        mureilbuilder.check_section_exists(full_config, self.config['global'])
        self.global_config = full_config[self.config['global']]
        globalconfig.pre_data_global_calcs(self.global_config)

        # Now check the dispatch_order, to get a list of the generators
        for gen in self.config['dispatch_order']:
            self.config_spec += [(gen, None, None)]

        self.update_from_config_spec()
        self.check_config()
        
        self.dispatch_order = self.config['dispatch_order']
        
        # Set up the data class and get the data
        self.data = mureilbuilder.create_instance(full_config, self.global_config, self.config['data'], 
            mureilbase.DataSinglePassInterface)
        self.global_config['data_ts_length'] = self.data.get_ts_length()
        globalconfig.post_data_global_calcs(self.global_config)

        # Instantiate the generator objects, set their data, determine their param requirements
        param_count = 0
        self.gen_list = {}
        self.gen_params = {}

        for i in range(len(self.dispatch_order)):
            gen_type = self.dispatch_order[i]

            # Build the generator instances
            gen = mureilbuilder.create_instance(full_config, self.global_config, 
                self.config[gen_type], singlepassgenerator.SinglePassGeneratorBase)
            self.gen_list[gen_type] = gen

            # Supply data as requested by the generator
            mureilbuilder.supply_single_pass_data(gen, self.data, gen_type)

            # Determine how many parameters this generator requires and
            # allocate the slots in the params list
            params_req = gen.get_param_count()
            if (params_req == 0):
                self.gen_params[gen_type] = (0, 0)
            else:
                self.gen_params[gen_type] = (param_count, 
                    param_count + params_req)
            param_count += params_req
        
        self.param_count = param_count
        
        self.is_configured = True
    
    
    def get_config_spec(self):
        return [
            ('data', None, 'Data'),
            ('global', None, 'Global'),
            ('output_file', None, 'ge.pkl'),
            ('dispatch_order', mureilbuilder.make_string_list, None),
            ('do_plots', mureilbuilder.string_to_bool, False),
            ('year_list', mureilbuilder.make_string_list, None),
            ('carbon_price_list', mureilbuilder.make_int_list, None),
            ('discount_rate', float, 0.0)
            ]


    def run(self, extra_data):
        if (not self.is_configured):
            msg = 'run requested, but GeMureilMaster is not configured'
            logger.critical(msg)
            raise mureilexception.ConfigException(msg, {})

        # Read in the json data for generator capacity
        self.load_js(extra_data)
        
        all_years_out = {}

        # Compute an annual total for generation
        output_multiplier = (self.global_config['variable_cost_mult'] /
            self.global_config['time_period_yrs'])

        cuml_cost = 0.0

        for year_index in range(len(self.config['year_list'])):
            
            ## MG - this is a hack. The config should be set with all
            ## of the values at the start, and then be passed the year,
            ## not have them updated each time. This is ok here as it's
            ## only evaluated once anyway.
           
            results = self.evaluate_results(year_index)

            year = self.config['year_list'][year_index]

            # print results['gen_desc']
            
            all_years_out[str(year)] = year_out = {}
            
            # Output, in MWh
            year_out['output'] = output_section = {}
            
            # Cost, in $M
            year_out['cost'] = cost_section = {}
            
            # Total carbon emissions
            year_out['co2_tonnes'] = 0.0
            
            # Total demand, in MWh per annum
            for generator_type, value in results['other']:
                if value is not None:
                    if 'ts_demand' in value:
                        year_out['demand'] = '{:.2f}'.format(
                            abs(sum(value['ts_demand'])) * self.global_config['timestep_hrs'] *
                            output_multiplier)
       
            # Total output, in MWh per annum
            for generator_type, values in results['output']:
                output_section[generator_type] = '{:.2f}'.format(
                    sum(values) * self.global_config['timestep_hrs'] *
                    output_multiplier)
    
            # Total cost, per decade
            this_period_cost = 0.0
            for generator_type, value in results['cost']:
                cost_section[generator_type] = value
                this_period_cost += value
# or as a string:
#                cost_section[generator_type] = '{:.2f}'.format(value)

            # Total cumulative cost, with discounting
            # This assumes the costs are all incurred at the beginning of
            # each period (a simplification)
            year_out['period_cost'] = this_period_cost
            cuml_cost += this_period_cost / ((1 + (self.config['discount_rate'] / 100)) **
                (self.global_config['time_period_yrs'] * year_index))
            year_out['discounted_cumulative_cost'] = cuml_cost
    
            for generator_type, value in results['other']:
                if value is not None:
                    if 'reliability' in value:
                        year_out['reliability'] = value['reliability']
                    if 'carbon' in value:
                        year_out['co2_tonnes'] += value['carbon']

            if 'reliability' not in year_out:
                year_out['reliability'] = 100

        return all_years_out
    
    
    def load_js(self, json_data):
        """ Input: JSON data structure with info on generators and demand management
                   at different time periods.
            Output: None
            Reads in the data and computes the params for each time period.
        """
        
        generators = json.loads(json_data)['selections']['generators']

        ## TODO - this isn't at all flexible, but will do for the first demo.
        ## Only coal, gas, wind and solar are handled, and only one of each
        ## hydro is awaiting a rainfall-based model.

        self.total_params = {}
        self.inc_params = {}

        gen_total_table = {}
        gen_inc_table = {}
        year_list = self.config['year_list']

        for gen in generators:
            if gen['type'] not in ['coal', 'gas', 'wind', 'solar']:
                msg = 'Generator ' + str(gen['type']) + ' ignored'
                logger.warning(msg)
            else:
                if gen['type'] not in gen_total_table:
                    new_total_table = numpy.zeros(len(self.config['year_list']))
                    new_inc_table = numpy.zeros(len(self.config['year_list']))
                    gen_total_table[gen['type']] = new_total_table
                    gen_inc_table[gen['type']] = new_inc_table

                this_total_table = gen_total_table[gen['type']]
                this_inc_table = gen_inc_table[gen['type']]

                # build date could be specified as earlier, so capex is not paid.
                build_index = numpy.where(numpy.array(year_list) == str(gen['decade']))
                if len(build_index[0] > 0):
                    build_index = build_index[0][0]
                else:
                    build_index = -1

                decommission_index = numpy.where(numpy.array(year_list) == str(gen['decomission']))
                if len(decommission_index[0] > 0):
                    decommission_index = decommission_index[0][0]
                else:
                    decommission_index = len(year_list) - 1

                # accumulate new capacity in the incremental list
                if build_index >= 0:
                    this_inc_table[build_index] += gen['capacity']                    
                
                # and add the new capacity to the total across all years until decommissioning
                start_fill = build_index
                if (build_index == -1):
                    start_fill = 0
                for i in range(start_fill, decommission_index + 1):
                    this_total_table[i] += gen['capacity']
                    
        for i in range(0, len(year_list)):
            this_total_params = numpy.zeros(4)
            this_inc_params = numpy.zeros(4)
            
            for gen_type in ['coal', 'wind', 'solar', 'gas']:
                param_ptr = self.gen_params[gen_type]
                # check if this generator takes any parameters at all before writing to it
                if (param_ptr[0] < param_ptr[1]) and (gen_type in gen_total_table):
                    this_total_params[param_ptr[0]] = gen_total_table[gen_type][i]
                    this_inc_params[param_ptr[0]] = gen_inc_table[gen_type][i]

            self.total_params[str(year_list[i])] = this_total_params
            self.inc_params[str(year_list[i])] = this_inc_params
    
        self.demand_settings = json.loads(json_data)['selections']['demand']

    
    def finalise(self):
        pass

 
            
    def calc_cost(self, ts_demand, total_params, inc_params, save_result=False):

        rem_demand = numpy.array(ts_demand, dtype=float)
        cost = 0

        for gen_type in self.dispatch_order:
            gen = self.gen_list[gen_type]
            gen_ptr = self.gen_params[gen_type]

            this_params = numpy.concatenate((total_params[gen_ptr[0]:gen_ptr[1]],
                inc_params[gen_ptr[0]:gen_ptr[1]]))

            (this_cost, this_ts) = gen.calculate_cost_and_output(
                this_params, rem_demand, save_result)

            cost += this_cost
            rem_demand -= this_ts
            
        return cost


    def evaluate_results(self, year_index):
        """Collect a dict that includes all the calculated results from a
        run for that year.
        
        Inputs:
            year: an index for the current year, indexing self.config['year_list']
            
        Outputs:
            results: a dict containing:
                gen_desc: list of tuples of (gen_type, desc) 
                    desc are strings describing
                    the generator type and the capacity or other parameters.
                cost: list of tuples of (gen_type, cost)
                output: list of tuples of (gen_type, output)
                other: list of tuples of (gen_type, other saved data)
        """
        
        year = self.config['year_list'][year_index]
        
        total_params = self.total_params[year]
        inc_params = self.inc_params[year]
        
        ts_demand = numpy.zeros(self.data.get_ts_length(), dtype=float)

        # Set the year-dependent values
        # TODO - this is a hack, and is not thread-safe. Remove once
        # there is a proper decade by decade system.
        self.gen_list['demand'].update_config({'year': year})
        self.gen_list['demand'].update_config(self.demand_settings[year])
        for gen_type in self.dispatch_order:
            self.gen_list[gen_type].update_config({'carbon_price': 
                self.config['carbon_price_list'][year_index]})

        self.calc_cost(ts_demand, total_params, inc_params, save_result=True)
        
        results = {}
        results['gen_desc'] = []
        results['cost'] = []
        results['output'] = []
        results['capacity'] = []
        results['other'] = []
        
        for gen_type in self.dispatch_order:
            gen = self.gen_list[gen_type]
            results['gen_desc'].append((gen_type, gen.interpret_to_string()))

            saved_result = gen.get_saved_result()
            results['capacity'].append((gen_type, saved_result['capacity']))
            results['cost'].append((gen_type, saved_result['cost']))
            results['output'].append((gen_type, saved_result['output']))
            results['other'].append((gen_type, saved_result['other']))

        return results
        
