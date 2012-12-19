import numpy as np
import pickle
import time

import tools.mureilbuilder as mureilbuilder
import tools.configurablebase as configurablebase
import tools.mureilexception as mureilexception
import tools.mureiloutput as mureiloutput
import tools.mureilbase as mureilbase

import generator.singlepassgenerator as singlepassgenerator
import logging
import copy

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
        full_conf[self.config['global']] = self.global_conf

        for gen_type in self.dispatch_order:
            gen = getattr(self, gen_type)
            full_conf[self.config[gen_type]] = gen.get_config()

        return full_conf

     
    def set_config(self, full_config):
    
        self.full_config = copy.deepcopy(full_config)
        config_spec = self.get_config_spec()

        # Apply defaults and new config values, to be prepared for flags
        new_config = mureilbuilder.collect_defaults(config_spec)
        new_config.update(self.full_config['Master'])
        new_config['section'] = 'Master'

        # Put the new_config back into the full_config, so flags can be applied
        self.full_config['Master'] = new_config
        mureilbuilder.apply_flags(self.full_config, self.full_config['flags'])
        del self.full_config['flags']
        new_config = self.full_config['Master']

        # Apply conversions to config
        mureilbuilder.apply_conversions(new_config, config_spec)

        # And check that all of the required parameters are there
        mureilbuilder.check_required_params(new_config, config_spec, self.__class__.__name__)

        # Now check what's happening in dispatch_order, to get a list of the generators
        for gen in new_config['dispatch_order']:
            config_spec += [(gen, None, None)]

        # And check again that all of the required parameters are there, including all the
        # generator details
        mureilbuilder.check_required_params(new_config, config_spec, self.__class__.__name__)

        # And check that there aren't any extras
        mureilbuilder.check_for_extras(new_config, config_spec, self.__class__.__name__)

        self.config = new_config
        self.dispatch_order = self.config['dispatch_order']

        # And get the global variables
        mureilbuilder.check_section_exists(self.full_config, __name__, self.config['global'])
        self.global_conf = self.full_config[self.config['global']]
        
        # Convert a few of them, and pre-calculate more useful values for some of them
        global_spec = [('timestep_mins', float, None), ('time_period_yrs', float, None)]
        mureilbuilder.apply_conversions(self.global_conf, global_spec)
        
        if 'timestep_mins' in self.global_conf:
            self.global_conf['timestep_hrs'] = float(self.global_conf['timestep_mins']) / 60
        elif 'timestep_hrs' in self.global_conf:
            self.global_conf['timestep_mins'] = float(self.global_conf['timestep_hrs']) * 60
       
        # Set up the data class and get the data
        mureilbuilder.check_section_exists(self.full_config, __name__, self.config['data'])
        data_config = self.full_config[self.config['data']]
        data_config['global'] = self.global_conf
        self.data = mureilbuilder.create_instance(data_config, self.config['data'], mureilbase.DataSinglePassInterface)
        self.data_dict = {}
        self.data_dict['ts_wind'] = self.data.wind_data()
        self.data_dict['ts_solar'] = self.data.solar_data()
        self.data_dict['ts_demand'] = self.data.demand_data()
        
        # Need to know the data length to compute variable_cost_mult - to extrapolate the variable
        # cost along the whole time period being modelled. Some NPV discounting could also be
        # incorporated with a discount rate parameter.
        if 'variable_cost_mult' not in self.global_conf:
            if 'time_period_yrs' in self.global_conf and 'timestep_hrs' in self.global_conf:
                data_samples = len(self.data_dict['ts_demand'])
                yrs_of_data = ((self.global_conf['timestep_hrs'] * float(data_samples)) /
                    (365.25 * 24))
                self.global_conf['variable_cost_mult'] = (self.global_conf['time_period_yrs'] /
                    yrs_of_data)
    
        # Get the algorithm config
        mureilbuilder.check_section_exists(self.full_config, __name__, self.config['algorithm'])
        algorithm_config = self.full_config[self.config['algorithm']]
        
        # Instantiate the generator objects, set their data, determine their param requirements
        param_count = 0
        for i in range(len(self.dispatch_order)):
            gen_type = self.dispatch_order[i]
            section = self.config[gen_type]

            mureilbuilder.check_section_exists(self.full_config, __name__, self.config[gen_type])
            conf_temp = self.full_config[section]
            conf_temp['global'] = self.global_conf

            # Build the generator instances
            setattr(self, gen_type, mureilbuilder.create_instance(conf_temp, section,
                singlepassgenerator.SinglePassGeneratorBase))
            gen = getattr(self, gen_type)

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
                setattr(self, gen_type + '_ptr', (0, 0))
            else:
                setattr(self, gen_type + '_ptr', (param_count, 
                    param_count + params_req))
            param_count += params_req
        
        self.param_count = param_count
        
        # Instantiate the algorithm
        algorithm_config['min_len'] = param_count
        algorithm_config['max_len'] = param_count
        algorithm_config['gene_test_callback'] = self.gene_test
        algorithm_config['global'] = self.global_conf
        self.algorithm = mureilbuilder.create_instance(algorithm_config, self.config['algorithm'], mureilbase.ConfigurableInterface)

        self.is_configured = True
        self.log_initial()
    
    
    def get_config_spec(self):
        return [
            ('algorithm', None, 'Algorithm'),
            ('data', None, 'Data'),
            ('global', None, 'Global'),
            ('iterations', int, 100),
            ('output_file', None, 'mureil.pkl'),
            ('dispatch_order', mureilbuilder.make_string_list, None),
            ('optim_type', None, 'missed_supply'),
            ('timestep_mins', int, 60),
            ('do_plots', mureilbuilder.string_to_bool, False)
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
    
    
    def log_initial(self):
        """input: None
        output: None
        prints values, scores, ect. at beginning
        """

        population = self.algorithm.get_population()
        num = 0
        sum = 0
        for gene in population.genes:
            num += 1
            sum += gene.score
        logger.debug('average score before: %f', float(sum)/num)
        return None


    def finalise(self):
        """input: None
        output: None
        prints values, scores, ect. at end
        """

        input_data = self.algorithm.get_final()
        self.algorithm.finalise()
        
        (population, clones_data, best_gene_data) = input_data
        
        num = 0
        sum = 0
        for gene in population.genes:
            num += 1
            sum += gene.score
        optim = [[],-1e1000,-1]
        for data in best_gene_data:
            if data[1] > optim[1]:
                optim = data
        logger.info('best gene was: %s', str(optim[0]))
        logger.info('on loop %i, with score %f', optim[2], optim[1])
        for data in clones_data:
            if data[1] > optim[1]:
                optim = data
        logger.debug('%i nuke/s dropped', len(clones_data))
        logger.debug('average score after: %f', float(sum)/num)   

        if len(optim[0]) > 0:
            # Protect against an exception before there are any params
            results = self.evaluate_results(optim[0])
                
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

        full_conf = self.get_full_config()
        mureiloutput.clean_config_for_pickle(full_conf)
        pickle_dict['config'] = full_conf
    
        pickle_dict['best_results'] = results
        pickle_dict['ts_demand'] = self.data_dict['ts_demand']

        if self.config['do_plots']:
            mureiloutput.plot_timeseries(results['output'], self.data_dict['ts_demand'])

        mureiloutput.pickle_out(pickle_dict, self.config['output_file'])
        
        return None


    def calc_cost(self, gene, save_result=False):

        params = np.array(gene)

        if self.config['optim_type'] == 'match_demand':
        
            rem_demand = np.array(self.data_dict['ts_demand'])

            (solar_cost, solar_ts) = self.solar.calculate_cost_and_output(
                params[self.solar_ptr[0]:self.solar_ptr[1]], rem_demand, save_result)
            rem_demand -= solar_ts
            
            (wind_cost, wind_ts) = self.wind.calculate_cost_and_output(
                params[self.wind_ptr[0]:self.wind_ptr[1]], rem_demand, save_result)
            rem_demand -= wind_ts

            cost = abs(rem_demand).sum()/1000.0  #now in GW

        elif self.config['optim_type'] == 'missed_supply':

            rem_demand = np.array(self.data_dict['ts_demand'], dtype=float)
            cost = 0

            for gen_type in self.dispatch_order:
                gen = getattr(self, gen_type)
                gen_ptr = getattr(self, gen_type + '_ptr')

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
            gen = getattr(self, gen_type)    
            results['gen_desc'].append((gen_type, gen.interpret_to_string()))

            saved_result = gen.get_saved_result()
            results['capacity'].append((gen_type, saved_result['capacity']))
            results['cost'].append((gen_type, saved_result['cost']))
            results['output'].append((gen_type, saved_result['output']))
            results['other'].append((gen_type, saved_result['other']))

        return results
        
        
    def gene_test(self, gene):
        """input: list
        output: float
        takes the gene.values, tests it and returns the genes score
        """
        score = -1 * self.calc_cost(gene)
        return score
