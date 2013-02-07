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
from collections import defaultdict
from os import path

from tools import mureilbuilder, mureilexception, mureiloutput, globalconfig
from tools import configurablebase, mureilbase
from generator import singlepassgenerator
from demand import temperaturedemand

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

        # TODO ASAP - this only works with the hard-coded file. Make it more
        # like simplemureilmaster.py.
        self.data_dict = {}
        self.data_dict['ts_wind'] = numpy.array(self.data.wind_data(), dtype=float)
        self.data_dict['ts_solar'] = numpy.array(self.data.solar_data(), dtype=float)
        self.data_dict['ts_demand'] = numpy.array(self.data.demand_data(), dtype=float)
        self.data_dict['demand_drivers'] = self.data.demand_drivers()
        self.global_config['data_ts_length'] = len(self.data_dict['ts_demand'])
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
            data_req = gen.get_data_types()
            new_data_dict = {}
            for key in data_req:
                new_data_dict[key] = self.data_dict[key]    
            gen.set_data(new_data_dict)

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
        
        # and read in the json data for generator capacity
        self.load_js(extra_data)
        
        # and load the data for the demand model
        self.demand_settings = json.loads(extra_data)['selections']['demand']    

        self.is_configured = True
    
    
    def get_config_spec(self):
        return [
            ('data', None, 'Data'),
            ('global', None, 'Global'),
            ('output_file', None, 'ge.pkl'),
            ('dispatch_order', mureilbuilder.make_string_list, None),
            ('do_plots', mureilbuilder.string_to_bool, False),
            ('year_list', mureilbuilder.make_string_list, None)
            ]


    def run(self):
        if (not self.is_configured):
            msg = 'run requested, but GeMureilMaster is not configured'
            logger.critical(msg)
            raise mureilexception.ConfigException(msg, 'GeMureilMaster.run', {})
    
        return None
    
    
    def load_js(self, json_data):
        """ Input: JSON data structure with info on generators and demand management
                   at different time periods.
            Output: None
            Reads in the data and computes the params for each time period.
        """
        
        generators = json.loads(json_data)['selections']['generators']

        ## TODO - this isn't at all flexible, but will do for the demo.
        ## Only coal, gas, wind and solar are handled, and only one of each
        ## hydro is awaiting an optimisable-capacity model

        self.params = {}

        gen_list = {}
        year_list = self.config['year_list']

        for gen in generators:
            if gen['type'] not in ['coal', 'gas', 'wind', 'solar']:
                msg = 'Generator ' + str(gen['type']) + ' ignored'
                logger.warning(msg)
            else:
                if gen['type'] not in gen_list:
                    new_list = numpy.zeros(len(self.config['year_list']))
                    gen_list[gen['type']] = new_list

                this_list = gen_list[gen['type']]

                build_index = numpy.where(numpy.array(year_list) == str(gen['decade']))
                if build_index[0]:
                    build_index = build_index[0][0]
                else:
                    build_index = 0

                decommission_index = numpy.where(numpy.array(year_list) == str(gen['decomission']))
                if decommission_index[0]:
                    decommission_index = decommission_index[0][0]
                else:
                    decommission_index = len(year_list) - 1

                # Assumes the plant is decommissioned at the end of the decade specified by decommissioning date
                for i in range(build_index, decommission_index + 1):
                    this_list[i] += gen['capacity']

        for i in range(0, len(year_list)):
            # This code assumes only one param per type, a simplification for the demo.
            this_params = numpy.zeros(4)
            for gen_type in ['coal', 'wind', 'solar', 'gas']:
                param_ptr = self.gen_params[gen_type]
                if (param_ptr[0] < param_ptr[1]) and (gen_type in gen_list):
                    this_params[param_ptr[0]] = gen_list[gen_type][i]

            self.params[str(year_list[i])] = this_params
    

    
    def finalise(self):
        """input: None
        output: None
        prints values, scores, ect. at end
        """

        all_years_out = defaultdict(dict)

        for year in self.config['year_list']:
            
            ### MG - this is a hack - the model should select which year in
            ### the calc_cost function. tbd when multi-time-period is done.
            ### also the models that require ts_demand (particularly the
            ### missed_supply) will need to be updated with the current value,
            ### not yet done.
            ### and the demand model should be selectable by config, tbd
            
            self.data_dict['ts_demand'] = temperaturedemand.calculate_demand(
                self.data_dict['demand_drivers'], self.demand_settings[str(year)], str(year), 
                self.global_config['timestep_hrs'])
        
            results = self.evaluate_results(self.params[str(year)])

            #print results['gen_desc']
            
            all_years_out[str(year)] = year_out = defaultdict(dict)
            
            # Output, in MWh
            year_out['output'] = output_section = defaultdict(dict)
            
            # Cost, in $M
            year_out['cost'] = cost_section = defaultdict(dict)
            
            # Total demand, in MWh
            year_out['demand'] = '{:.2f}'.format(
                numpy.sum(self.data_dict['ts_demand']) * self.global_config['timestep_hrs'])
    
            for generator_type, values in results['output']:
                output_section[generator_type] = '{:.2f}'.format(
                    sum(values) * self.global_config['timestep_hrs'])
    
            for generator_type, value in results['cost']:
                cost_section[generator_type] = value
# or as a string:
#                cost_section[generator_type] = '{:.2f}'.format(value)

        return all_years_out
        
            
    def calc_cost(self, gene, save_result=False):

        params = numpy.array(gene)

        rem_demand = numpy.array(self.data_dict['ts_demand'], dtype=float)
        cost = 0

        for gen_type in self.dispatch_order:
            gen = self.gen_list[gen_type]
            gen_ptr = self.gen_params[gen_type]

            (this_cost, this_ts) = gen.calculate_cost_and_output(
                params[gen_ptr[0]:gen_ptr[1]], rem_demand, save_result)

            cost += this_cost
            rem_demand -= this_ts
            
        return cost


    def evaluate_results(self, params):
        """Collect a dict that includes all the calculated results from a
        run with params.
        
        Inputs:
            params: list of numbers, typically the best output from a run.
            
        Outputs:
            results: a dict containing:
                gen_desc: list of tuples of (gen_type, desc) 
                    desc are strings describing
                    the generator type and the capacity or other parameters.
                cost: list of tuples of (gen_type, cost)
                output: list of tuples of (gen_type, output)
                other: list of tuples of (gen_type, other saved data)
        """
        
        # First evaluate with these parameters
        self.calc_cost(params, save_result=True)
        
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
        
