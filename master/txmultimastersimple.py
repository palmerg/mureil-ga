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
from os import path

from tools import mureilbuilder, mureilexception, mureiloutput, mureiltypes, globalconfig
from tools import mureilbase, configurablebase

from generator import txmultigeneratorbase

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
        
        start_values_min = numpy.array([[]]).reshape((len(self.config['run_periods']), 0))
        start_values_max = numpy.array([[]]).reshape((len(self.config['run_periods']), 0))

        for i in range(len(self.dispatch_order)):
            gen_type = self.dispatch_order[i]

            # Build the generator instances
            gen = mureilbuilder.create_instance(full_config, self.global_config, 
                self.config[gen_type], txmultigeneratorbase.TxMultiGeneratorBase,
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

                run_period_len = len(self.config['run_periods'])
                (starts_min, starts_max) = gen.get_param_starts()
                starts_min = numpy.array(starts_min)
                starts_max = numpy.array(starts_max)

                if starts_min.size == 0:
                    start_values_min = numpy.hstack((start_values_min, (
                        (numpy.ones((run_period_len, params_req)) * 
                        self.global_config['min_param_val']).tolist())))
                else:
                    start_values_min = numpy.hstack((start_values_min, starts_min))

                if starts_max.size == 0:
                    start_values_max = numpy.hstack((start_values_max, (
                        (numpy.ones((run_period_len, params_req)) * 
                        self.global_config['max_param_val']).tolist())))
                else:
                    start_values_max = numpy.hstack((start_values_max, starts_max))

            param_count += params_req

        start_values_min = start_values_min.reshape(run_period_len * param_count)
        start_values_max = start_values_max.reshape(run_period_len * param_count)

        self.param_count = param_count
        # Check that run_periods increases by time_period_yrs
        self.run_periods = self.config['run_periods']
        if len(self.run_periods) > 1:
            run_period_diffs = numpy.diff(self.run_periods)
            if (not (min(run_period_diffs) == self.global_config['time_period_yrs']) or
                not (max(run_period_diffs) == self.global_config['time_period_yrs'])):
                raise mureilexception.ConfigException('run_periods must be separated by time_period_yrs', {})

        self.period_count = len(self.run_periods)
        self.total_param_count = param_count * self.period_count

        # Check if 'extra_data' has been provided, as a full gene to start at.
        # extra_data needs to be a dict with entry 'start_gene' that is a list
        # of integer values the same length as param_count.
        if extra_data is not None:
            if 'start_gene' in extra_data:
                if not (len(start_values_min) == self.total_param_count):
                    msg = ('extra_data of start_gene passed to txmultimastersimple. ' +
                        'Length expected = {:d}, found = {:d}'.format(self.total_param_count, 
                        len(start_values_min)))
                    raise mureilexception.ConfigException(msg, {})

                start_values_min = extra_data['start_gene']
                start_values_max = extra_data['start_gene']
       
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
                    self.output_results(iteration=i)
                    
        except mureilexception.AlgorithmException:
            # Insert here something special to do if debugging
            # such an exception is required.
            # self.finalise will be called by the caller
            raise
    
        logger.critical('Run time: %.2f seconds', (time.time() - start_time))

        results = self.output_results(iteration=self.config['iterations'], final=True)
        
        return results
    
    
    def output_results(self, final=False, iteration=0):
    
        (best_params, opt_data) = self.algorithm.get_final()

        if len(best_params) > 0:
            # Protect against an exception before there are any params
            results = self.evaluate_results(best_params)

            logger.info('======================================================')
            logger.info('Total cost ($M): {:.2f}, including carbon (MT): {:.2f}, terminal value ($M): {:.2f}'.format(
                results['totals']['cost'], results['totals']['carbon'] * 1e-6, results['totals']['terminal_value']))
            logger.info('======================================================')

            ts_demand = {}
    
            # Now iterate across the periods, and then across the generators
            for period in self.run_periods:
                period_results = results['periods'][period]
                logger.info('------------------------------------------------------')
                logger.info('PERIOD ' + str(period) + ':')
                logger.info('------------------------------------------------------')
                logger.info('Period cost ($M): {:.2f}, carbon (MT): {:.2f}'.format(
                    period_results['totals']['cost'], 
                    period_results['totals']['carbon'] * 1e-6))

                if 'demand' in self.dispatch_order:
                    ts_demand[period] = period_results['demand']['other']['ts_demand']
                else:
                    ts_demand[period] = self.data.get_timeseries('ts_demand')
            
                period_results['totals']['demand'] = (numpy.sum(ts_demand[period]) *
                    self.global_config['time_scale_up_mult'] * self.global_config['timestep_hrs'])
                logger.info('Period total demand (GWh): {:.2f}'.format(
                    period_results['totals']['demand'] / 1000))

                for gen_type, value in period_results['generators'].iteritems():
                    gen_string = value['desc_string']
                    gen_cost = value['cost']
                    gen_supply = value['total_supply_period']
                    logger.info(gen_type + ' ($M {:.2f}, GWh {:.2f}) : '.format(
                        gen_cost, gen_supply / 1000) + gen_string)

            logger.info('======================================================')

            pickle_dict = {}
            pickle_dict['opt_data'] = opt_data
            pickle_dict['best_params'] = best_params

            full_conf = self.get_full_config()
            mureiloutput.clean_config_for_pickle(full_conf)
            pickle_dict['config'] = full_conf

            pickle_dict['best_results'] = results
            pickle_dict['ts_demand'] = ts_demand

            if self.config['do_plots']:
                for period in self.run_periods:
                    plot_data = {}
                    for gen_type, value in results['periods'][period]['generators'].iteritems():
                        plot_data[gen_type] = value['aggregate_supply']
                        
                    this_final = final and (period == self.config['run_periods'][-1])
                    mureiloutput.plot_timeseries(plot_data, 
                        ts_demand[period], this_final, plot_title=(
                            str(period) + ' at iteration ' + str(iteration)))

            output_file = self.config['output_file']
            mureiloutput.pickle_out(pickle_dict, output_file)
        else:
            results = None

        return results
        

    def finalise(self):
        self.algorithm.finalise()

            
    def calc_cost(self, gene, full_results=False):
        """Calculate the total system cost for this gene. This function is called
        by the algorithm from a callback. The algorithm may set up multi-processing
        and so this calc_cost function (and all functions it calls) must be
        thread-safe. 
        This means that the function must not modify any of the 
        internal data of the objects. 
        """
        
        temp = numpy.array(gene)
        params_set = temp.reshape(self.period_count, self.param_count)

        gen_state_handles = {}
        for gen_type in self.dispatch_order:
            gen_state_handles[gen_type] = (
                self.gen_list[gen_type].get_startup_state_handle())        

        cost = 0

        if full_results:
            results = {'totals': {}, 'periods': {}, 'terminal': {}}
            total_carbon = 0.0

        for i in range(len(self.run_periods)):
            period = self.run_periods[i]
            params = params_set[i]

            if full_results:
                period_carbon = 0.0
                results['periods'][period] = period_results = {'generators': {}, 'totals': {}}
                results['terminal'] = {'totals': {}, 'generators': {}}

            # supply_request is the running total, modified here
            if 'demand' in self.dispatch_order:
                supply_request = numpy.zeros(self.data.get_ts_length(), dtype=float)
            else:
                supply_request = numpy.array(self.data.get_timeseries('ts_demand'), dtype=float)

            period_cost = 0

            for gen_type in self.dispatch_order:
                gen = self.gen_list[gen_type]
                gen_ptr = self.gen_params[gen_type]

                if full_results:
                    (this_sites, this_cost, this_supply, 
                        period_results['generators'][gen_type]) = gen.calculate_time_period_simple( 
                        gen_state_handles[gen_type], period, params[gen_ptr[0]:gen_ptr[1]], 
                        supply_request, full_results=True)
                    period_carbon += numpy.sum(period_results['generators'][gen_type]['carbon_emissions_period'])
                else:
                    (this_sites, this_cost, this_supply) = gen.calculate_time_period_simple( 
                        gen_state_handles[gen_type], period, params[gen_ptr[0]:gen_ptr[1]], 
                        supply_request)

                period_cost += this_cost
                supply_request -= this_supply

            if full_results:
                period_results['totals']['cost'] = period_cost
                period_results['totals']['carbon'] = period_carbon
                total_carbon += period_carbon
            
            cost += period_cost

        # calculate the terminal value at the end of the last period
        total_terminal_value = 0.0

        final_period = self.run_periods[-1]
        for gen_type in self.dispatch_order:
            gen = self.gen_list[gen_type]
            terminal_value, site_terminal_value = gen.get_terminal_value(final_period, 
                gen_state_handles[gen_type])

            if full_results:
                results['terminal']['generators'][gen_type] = {'total_value': terminal_value, 
                    'site_value': site_terminal_value}
            total_terminal_value += terminal_value
            
        cost -= total_terminal_value

        if full_results:
            results['totals']['cost'] = cost
            results['totals']['carbon'] = total_carbon
            results['totals']['terminal_value'] = total_terminal_value
            return cost, results
        else:
            return cost


    def evaluate_results(self, params):
        """Collect a dict that includes all the calculated results from a
        run with params.
        
        Inputs:
            params: list of numbers, typically the best output from a run.
            
        Outputs:
            results: a dict of gen_type: gen_results
            where gen_results is the output from calculate_time_period_simple in
            txmultigenerator.py (or subclass), with full_results = True.
        """
        
        cost, results = self.calc_cost(params, full_results=True)
        return results
        
        
    def gene_test(self, gene):
        """input: list
        output: float
        takes the gene.values, tests it and returns the genes score
        """
        score = -1 * self.calc_cost(gene)
        return score
