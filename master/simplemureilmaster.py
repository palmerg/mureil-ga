import numpy as np
import pickle
import time

import tools.mureilbuilder as mureilbuilder
import tools.mureilbase as mureilbase
import tools.mureilexception as mureilexception
import tools.mureiloutput as mureiloutput

import generator.singlepassgenerator as singlepassgenerator
import logging

logger = logging.getLogger(__name__)

class SimpleMureilMaster(mureilbase.MasterInterface):
    def __init__(self):
        self.config = self.get_default_config()
        self.is_configured = False

    def get_config(self):
        return self.config

    def get_full_config(self):
        if not self.is_configured:
            return None
        
        # Will return full_config, as recorded, but updated from objects to get
        # defaults etc.
        full_conf = self.full_config
        full_conf['Master'].update(self.config)
        full_conf[self.config['data']].update(self.data.get_config())
        full_conf[self.config['hydro']].update(self.hydro.get_config())
        full_conf[self.config['solar']].update(self.solar.get_config())
        full_conf[self.config['wind']].update(self.wind.get_config())
        full_conf[self.config['fossil']].update(self.fossil.get_config())
        full_conf[self.config['algorithm']].update(self.algorithm.get_config())

        return full_conf

        
    def set_config(self, full_config):
        self.config.update(full_config['Master'])
        self.full_config = full_config

        # First, set up the data class and get the data
        data_config = full_config[self.config['data']]
        self.data = mureilbuilder.create_instance(data_config, self.config['data'], mureilbase.DataSinglePassInterface)
        self.data_dict = {}
        self.data_dict['ts_wind'] = self.data.wind_data()
        self.data_dict['ts_solar'] = self.data.solar_data()
        self.data_dict['ts_demand'] = self.data.demand_data()
        
        # Get the algorithm config
        if self.config['algorithm'] not in full_config:
            algorithm_config = {'module': 'geneticalgorithm', 'class' : 'Engine'}
            self.full_config[self.config['algorithm']] = algorithm_config
        else:
            algorithm_config = full_config[self.config['algorithm']]
        
        # Instantiate the generator objects, set their data, determine their param requirements and
        # set the param min/max
        self.gen_list = ['solar', 'wind', 'hydro', 'missed_supply', 'fossil']
        
        param_count = 0
        for i in range(len(self.gen_list)):
            gen_type = self.gen_list[i]
            conf_temp = mureilbuilder.check_default_module(gen_type, self)
            setattr(self, gen_type, mureilbuilder.create_instance(conf_temp, self.config[gen_type],
                singlepassgenerator.SinglePassGeneratorBase))
            gen = getattr(self, gen_type)
            gen.set_param_min_max(algorithm_config['min_size'], algorithm_config['max_size'])
            data_req = gen.get_data_types()
            new_data_dict = {}
            for key in data_req:
                new_data_dict[key] = self.data_dict[key]    
            gen.set_data(new_data_dict)
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
        self.algorithm = mureilbuilder.create_instance(algorithm_config, self.config['algorithm'], mureilbase.ConfigurableInterface)

        self.is_configured = True
        self.log_initial()
    
    
    def get_default_config(self):
        config = {
            'module' : 'simplemureilmaster',
            'class' : 'SimpleMureilMaster',
            'algorithm' : 'Algorithm',
            'solar' : 'Solar',
            'wind' : 'Wind',
            'hydro' : 'Hydro',
            'fossil' : 'Fossil',
            'missed_supply': 'MissedSupply',
            'data' : 'Data',
            'optim_type' : 'missed_supply',
            'iterations' : 25,
            'output_file' : 'mureil_sample.pkl',
            'cost_calc' : 'linear_install'
        }
        
        return config
    
    
    def get_default_module_configs(self, key):
        if (key == 'algorithm'):
            return {'module': 'geneticalgorithm', 'class' : 'Engine'}
        elif (key == 'solar') or (key == 'wind'):
            return {'module': 'generator.variablegeneratorbasic',
                'class': 'VariableGeneratorBasic'}
        elif (key == 'hydro'):
            return {'module': 'hydro.basicpumpedhydro', 'class': 'BasicPumpedHydro'}
        elif (key == 'fossil'):
            return {'module' : 'thermal.instantmaxthermal',
                'class': 'InstantMaxThermal'}
        elif (key == 'missed_supply'):
            return {'module' : 'missed_supply.linearmissedsupply', 
                'class': 'LinearMissedSupply'}
        else:
            ## TODO - throw an exception, e.g. for data which doesn't default to anything.
            return None
    

    def run(self):
        start_time = time.time()
        logger.critical('Run started at %s', time.ctime())

        if (not self.is_configured):
            msg = 'run requested, but simplemureilmaster is not configured'
            logger.critical(msg)
            raise mureilexception.ConfigException(msg, 'simplemureilmaster.run', {})
    
        try:
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

        results = self.evaluate_results(optim[0])
                
        # and print out the text strings
        strings = results['gen_desc']
        for pairs in strings:
            logger.info(pairs[0] + ': ' + pairs[1])
    
        pickle_dict = {}
        pickle_dict['best_gene_data'] = best_gene_data

        full_conf = self.get_full_config()
        mureiloutput.clean_config_for_pickle(full_conf)
        pickle_dict['config'] = full_conf
    
        pickle_dict['best_results'] = results

        mureiloutput.pickle_out(pickle_dict, self.config['output_file'])
        
        self.algorithm.finalise()
        
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

            (solar_cost, solar_ts) = self.solar.calculate_cost_and_output(
                params[self.solar_ptr[0]:self.solar_ptr[1]], rem_demand, save_result)
            rem_demand -= solar_ts
            
            (wind_cost, wind_ts) = self.wind.calculate_cost_and_output(
                params[self.wind_ptr[0]:self.wind_ptr[1]], rem_demand, save_result)
            rem_demand -= wind_ts

            (hydro_cost, hydro_ts) = self.hydro.calculate_cost_and_output( 
                params[self.hydro_ptr[0]:self.hydro_ptr[1]], rem_demand, save_result)
            rem_demand -= hydro_ts

            (fossil_cost, fossil_ts) = self.fossil.calculate_cost_and_output(
                params[self.fossil_ptr[0]:self.fossil_ptr[1]], rem_demand, save_result)
            rem_demand -= fossil_ts

            (missed_supply_cost, missed_supply_ts) = (
                self.missed_supply.calculate_cost_and_output(
                params[self.missed_supply_ptr[0]:self.missed_supply_ptr[1]], 
                rem_demand, save_result))
            rem_demand -= missed_supply_ts

            cost = solar_cost + wind_cost + hydro_cost + fossil_cost + missed_supply_cost    

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
        
        for gen_type in self.gen_list:
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
