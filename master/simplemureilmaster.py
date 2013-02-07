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
import time
import logging
import copy
from os import path

from tools import mureilbuilder, mureilexception, mureiloutput, mureiltypes, globalconfig
from tools import mureilbase, configurablebase

from generator import singlepassgenerator

logger = logging.getLogger(__name__)

class SimpleMureilMaster(mureilbase.MasterInterface, configurablebase.ConfigurableBase):
    def get_full_config(self):
        if not self.is_configured:
            return None
        
        # Will return configs collected from all objects, assembled into full_config.
        full_conf = {}
        full_conf['Master'] = self.config
        full_conf[self.config['data']] = self.data.get_config()
        full_conf[self.config['algorithm']] = self.algorithm.get_config()
        full_conf[self.config['global']] = self.global_config

        for gen_type in self.dispatch_order:
            full_conf[self.config[gen_type]] = self.gen_list[gen_type].get_config()

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
        
        # Set up the data class and get the data, and compute the global parameters
        self.data = mureilbuilder.create_instance(full_config, self.global_config, self.config['data'], 
            mureilbase.DataSinglePassInterface)
        self.global_config['data_ts_length'] = self.data.get_ts_length()
        globalconfig.post_data_global_calcs(self.global_config)
        
        # Instantiate the generator objects, set their data, determine their param requirements
        param_count = 0
        self.gen_list = {}
        self.gen_params = {}
        start_values_min = []
        start_values_max = []
        
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
                new_data_dict[key] = self.data.get_timeseries(key)
                mureiltypes.check_ndarray_float(new_data_dict[key])
            gen.set_data(new_data_dict)

            # Determine how many parameters this generator requires and
            # allocate the slots in the params list
            params_req = gen.get_param_count()
            if (params_req == 0):
                self.gen_params[gen_type] = (0, 0)
            else:
                self.gen_params[gen_type] = (param_count, 
                    param_count + params_req)
                (starts_min, starts_max) = gen.get_param_starts()
                if len(starts_min) == 0:
                    start_values_min += ((np.ones(params_req) * self.global_config['min_param_val']).tolist())
                    start_values_max += ((np.ones(params_req) * self.global_config['max_param_val']).tolist())
                else:
                    start_values_min += starts_min
                    start_values_max += starts_max
            param_count += params_req
        
        self.param_count = param_count
        
        print start_values_min
        print start_values_max
        
        # Instantiate the genetic algorithm
        mureilbuilder.check_section_exists(full_config, self.config['algorithm'])
        algorithm_config = full_config[self.config['algorithm']]
        algorithm_config['min_len'] = algorithm_config['max_len'] = param_count
        algorithm_config['start_values_min'] = start_values_min
        algorithm_config['start_values_max'] = start_values_max
        algorithm_config['gene_test_callback'] = self.gene_test
        self.algorithm = mureilbuilder.create_instance(full_config, self.global_config,
            self.config['algorithm'], mureilbase.ConfigurableInterface)

        self.is_configured = True
    
    
    def get_config_spec(self):
        return [
            ('algorithm', None, 'Algorithm'),
            ('data', None, 'Data'),
            ('global', None, 'Global'),
            ('iterations', int, 100),
            ('output_file', None, 'mureil.pkl'),
            ('dispatch_order', mureilbuilder.make_string_list, None),
            ('optim_type', None, 'missed_supply'),
            ('do_plots', mureilbuilder.string_to_bool, False),
            ]


    def run(self):
        start_time = time.time()
        logger.critical('Run started at %s', time.ctime())

        if (not self.is_configured):
            msg = 'run requested, but simplemureilmaster is not configured'
            logger.critical(msg)
            raise mureilexception.ConfigException(msg, 'simplemureilmaster.run', {})
    
        try:
            self.algorithm.prepare_run()
            for i in range(self.config['iterations']):
                self.algorithm.do_iteration()
        except mureilexception.AlgorithmException:
            # Insert here something special to do if debugging
            # such an exception is required.
            # self.finalise will be called by the caller
            raise
    
        logger.critical('Run time: %.2f seconds', (time.time() - start_time))
        return None
    

    def finalise(self):
        """input: None
        output: None
        prints values, scores, ect. at end
        """

        (best_gene, best_gene_data) = self.algorithm.get_final()
        self.algorithm.finalise()
        
        if len(best_gene) > 0:
            # Protect against an exception before there are any params
            results = self.evaluate_results(best_gene)
                
            # and print out the text strings, accompanied by the costs
            strings = results['gen_desc']
            costs = results['cost']
            total_cost = 0.0
            for i in range(len(strings)):
                gen = strings[i][0]
                info = strings[i][1]
                cost = costs[i][1]
                total_cost += cost
                logger.info(gen + ' ($M {:.2f}) : '.format(cost) + info)
    
            logger.info('Total cost ($M): {:.2f}'.format(total_cost))
        else:
            results = None

        pickle_dict = {}
        # round the total cost to simplify regression comparison
        for i in range(len(best_gene_data)):
            best_gene_data[i][1] = round(best_gene_data[i][1], 0)
        pickle_dict['best_gene_data'] = best_gene_data
        pickle_dict['best_gene'] = best_gene

        full_conf = self.get_full_config()
        mureiloutput.clean_config_for_pickle(full_conf)
        pickle_dict['config'] = full_conf
    
        pickle_dict['best_results'] = results
        pickle_dict['ts_demand'] = self.data.get_timeseries('ts_demand')

        if self.config['do_plots']:
            mureiloutput.plot_timeseries(results['output'], 
                self.data.get_timeseries('ts_demand'))

        output_file = self.config['output_file']
        output_type = 'json' if output_file.endswith('json') else 'pickle' 
        
        if output_type == 'pickle':
            mureiloutput.pickle_out(pickle_dict, output_file)
        
        elif output_type in ('json', 'js'):
            
            import json
            import numpy

            class NumpyAwareJSONEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, numpy.ndarray) and obj.ndim == 1:
                        return [x for x in obj]
                    return json.JSONEncoder.default(self, obj)
            
            output_file = path.join(path.dirname(__file__), '..', output_file)
            with open(output_file, 'w') as f:
                json.dump(pickle_dict, f, cls=NumpyAwareJSONEncoder)
                
            
    def calc_cost(self, gene, save_result=False):

        params = np.array(gene)

        if self.config['optim_type'] == 'match_demand':
        
            rem_demand = np.array(self.data.get_timeseries('ts_demand'), dtype=float)
            mureiltypes.check_ndarray_float(rem_demand)            

            (solar_cost, solar_ts) = self.gen_list['solar'].calculate_cost_and_output(
                params[self.gen_params['solar'][0]:self.gen_params['solar'][1]], rem_demand, save_result)
            rem_demand -= solar_ts
            
            (wind_cost, wind_ts) = self.gen_list['wind'].calculate_cost_and_output(
                params[self.gen_params['wind'][0]:self.gen_params['wind'][1]], rem_demand, save_result)
            rem_demand -= wind_ts

            cost = abs(rem_demand).sum()/1000.0  #now in GW

        elif self.config['optim_type'] == 'missed_supply':

            # rem_demand is the running total, modified here
            rem_demand = np.array(self.data.get_timeseries('ts_demand'), dtype=float)
            mureiltypes.check_ndarray_float(rem_demand)            
            
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
        for val_type in ['capacity', 'cost', 'output', 'other']:
            results[val_type] = []

        for gen_type in self.dispatch_order:
            gen = self.gen_list[gen_type]
            results['gen_desc'].append((gen_type, gen.interpret_to_string()))

            saved_result = gen.get_saved_result()
            for val_type in ['capacity', 'cost', 'output', 'other']:
                results[val_type].append((gen_type, saved_result[val_type]))

        return results
        
        
    def gene_test(self, gene):
        """input: list
        output: float
        takes the gene.values, tests it and returns the genes score
        """
        score = -1 * self.calc_cost(gene)
        return score
