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

from generator import txmultigenerator

logger = logging.getLogger(__name__)

class TxMultiMasterSimple(mureilbase.MasterInterface, configurablebase.ConfigurableMultiBase):
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
                self.config[gen_type], singlepassgenerator.SinglePassGeneratorBase,
                self.config['run_periods'])
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
        self.run_periods = self.config['run_periods']
        self.period_count = len(self.run_periods)
        self.total_param_count = param_count * self.period_count
        
        # Instantiate the genetic algorithm
        mureilbuilder.check_section_exists(full_config, self.config['algorithm'])
        algorithm_config = full_config[self.config['algorithm']]
        algorithm_config['min_len'] = algorithm_config['max_len'] = self.total_param_count
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
            ('do_plots', mureilbuilder.string_to_bool, False),
            ('output_frequency', int, 500),
            ('run_periods', mureilbuilder.make_int_list, [2010])
            ]


    def run(self, extra_data=None):
        start_time = time.time()
        logger.critical('Run started at %s', time.ctime())

        if (not self.is_configured):
            msg = 'run requested, but txmultimastersimple is not configured'
            logger.critical(msg)
            raise mureilexception.ConfigException(msg, {})
    
        try:
            self.algorithm.prepare_run()
            for i in range(self.config['iterations']):
                self.algorithm.do_iteration()
                if ((self.config['output_frequency'] > 0) and
                    ((i % self.config['output_frequency']) == 0)):
                    logger.info('Interim results at iteration %d', i)
                    self.output_results()
                    
        except mureilexception.AlgorithmException:
            # Insert here something special to do if debugging
            # such an exception is required.
            # self.finalise will be called by the caller
            raise
    
        logger.critical('Run time: %.2f seconds', (time.time() - start_time))

        results = self.output_results(final=True)
        
        return results
    
    
    def output_results(self, final=False):
    
        ### TODO - update this
    
        (best_gene, best_gene_data) = self.algorithm.get_final()
        
        if len(best_gene) > 0:
            # Protect against an exception before there are any params
            results = self.evaluate_results(best_gene)

            if 'demand' in self.dispatch_order:
                ts_demand = results['other']['demand']['ts_demand']
            else:
                ts_demand = self.data.get_timeseries('ts_demand')
                
            # and print out the text strings, accompanied by the costs
            strings = results['gen_desc']
            costs = results['cost']
            total_cost = 0.0
            for gen in results['cost'].iterkeys():
                info = strings[gen]
                cost = costs[gen]
                total_cost += cost
                logger.info(gen + ' ($M {:.2f}) : '.format(cost) + info)
    
            logger.info('Total cost ($M): {:.2f}'.format(total_cost))
        else:
            results = None

        pickle_dict = {}
        pickle_dict['best_gene_data'] = best_gene_data
        pickle_dict['best_gene'] = best_gene

        full_conf = self.get_full_config()
        mureiloutput.clean_config_for_pickle(full_conf)
        pickle_dict['config'] = full_conf
    
        pickle_dict['best_results'] = results
        pickle_dict['ts_demand'] = ts_demand
    
        if self.config['do_plots']:
            mureiloutput.plot_timeseries(results['output'], 
                ts_demand, final)

        output_file = self.config['output_file']
        mureiloutput.pickle_out(pickle_dict, output_file)
  
        return results
        

    def finalise(self):
        self.algorithm.finalise()

            
    def calc_cost(self, gene):
        """Calculate the total system cost for this gene. This function is called
        by the algorithm from a callback. The algorithm may set up multi-processing
        and so this calc_cost function (and all functions it calls) must be
        thread-safe when save_result=False. 
        This means that the function must not modify any of the 
        internal data of the objects. 
        """
        
        params_set = gene.reshape(self.param_count, self.period_count)

        gen_state_handles = {}
        for gen_type in self.dispatch_order:
            gen_state_handles[gen_type] = (
                self.gen_list[gen_type].get_starting_state_handle())        

        cost = 0
        for i in range(len(self.run_periods)):
            period = self.run_periods[i]
            params = params_set[i]

            # supply_request is the running total, modified here
            if 'demand' in self.dispatch_order:
                supply_request = np.zeros(self.data.get_ts_length(), dtype=float)
            else:
                supply_request = np.array(self.data.get_timeseries('ts_demand'), dtype=float)

            period_cost = 0

            for gen_type in self.dispatch_order:
                gen = self.gen_list[gen_type]
                gen_ptr = self.gen_params[gen_type]

                (this_cost, this_supply) = gen.calculate_time_period_simple(self, 
                    gen_state_handles[gen_type], period, params[gen_ptr[0]:gen_ptr[1]], 
                    supply_request)

                period_cost += this_cost
                supply_request -= this_ts
            
            cost += period_cost
            
        return cost


    def evaluate_results(self, params):
        """Collect a dict that includes all the calculated results from a
        run with params.
        
        Inputs:
            params: list of numbers, typically the best output from a run.
            
        Outputs:
            results: a dict containing:
                gen_desc: dict of gen_type: desc 
                    desc are strings describing
                    the generator type and the capacity or other parameters.
                cost: dict of gen_type: cost
                output: dict of gen_type: output
                other: dict of gen_type: other saved data
        """
        
        # First evaluate with these parameters

        ### TODO - update this
#        self.calc_cost(params, save_result=True)
#            
        results = {}
#        results['gen_desc'] = {}
#        for val_type in ['capacity', 'cost', 'output', 'other']:
#            results[val_type] = {}
#
#        for gen_type in self.dispatch_order:
#            gen = self.gen_list[gen_type]
#            results['gen_desc'][gen_type] = gen.interpret_to_string()
#
#            saved_result = gen.get_saved_result()
#            for val_type in ['capacity', 'cost', 'output', 'other']:
#                results[val_type][gen_type] = saved_result[val_type]
#
        return results
        
        
    def gene_test(self, gene):
        """input: list
        output: float
        takes the gene.values, tests it and returns the genes score
        """
        score = -1 * self.calc_cost(gene)
        return score
