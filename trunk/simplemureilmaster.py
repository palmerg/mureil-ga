import numpy as np
import pickle

import mureilbuilder

class SimpleMureilMaster:
    def __init__(self):
        self.config = self.get_default_config()
        self.is_configured = False

    def get_config(self):
        return self.config

    def set_config(self, full_config):
        self.config.update(full_config['Master'])
        self.full_config = full_config

        # First, set up the data class and get the data
        data_config = full_config[self.config['data']]
        self.data_instance = mureilbuilder.create_instance(data_config)
        self.ts_wind = self.data_instance.wind_data()
        self.ts_solar = self.data_instance.solar_data()
        self.ts_demand = self.data_instance.demand_data()
        
        # Now, set the parameters defining the sim size from the data size
        self.nwind_stats = self.ts_wind.shape[1]
        self.nsolar_stats = self.ts_solar.shape[1]
        self.nsteps = self.ts_demand.shape[0]

        # Instantiate hydro object
        if self.config['hydro'] not in full_config:
            hydro_config = {'module': 'basicpumpedhydro', 'class': 'BasicPumpedHydro'}
        else:
            hydro_config = full_config[self.config['hydro']]
            
        self.hydro = mureilbuilder.create_instance(hydro_config)

        for gen_type in ['solar', 'wind', 'gas']:
            setattr(self, gen_type, self.get_default_generator_config(gen_type))
            x = getattr(self, gen_type)
            if self.config[gen_type] in full_config:
                mureilbuilder.check_param_names(x, full_config[self.config[gen_type]], 'simplemureilmaster_' + gen_type)
                x.update(full_config[self.config[gen_type]])

        # and set up the algorithm
        if self.config['algorithm'] not in full_config:
            algorithm_config = {'module': 'geneticalgorithm', 'class' : 'Engine'}
        else:
            algorithm_config = full_config[self.config['algorithm']]
        
        algorithm_config['min_len'] = self.nsolar_stats + self.nwind_stats
        algorithm_config['max_len'] = self.nsolar_stats + self.nwind_stats
        algorithm_config['gene_test_callback'] = self.gene_test
        
        self.algorithm = mureilbuilder.create_instance(algorithm_config)

        self.is_configured = True

        self.before(self.algorithm.get_population())
    
    def get_default_config(self):
        config = {
            'module' : 'simplemureilmaster',
            'class' : 'SimpleMureilMaster',
            'algorithm' : 'Algorithm',
            'solar' : 'Solar',
            'wind' : 'Wind',
            'hydro' : 'Hydro',
            'gas' : 'Gas',
            'data' : 'Data',
            'optim_type' : 'missed_supply',
            'iterations' : 25,
            'output_file' : 'mureil_sample.pkl',
            'cost_calc' : 'linear_install'
        }
        
        return config
    
    def get_default_generator_config(self, gen_type):
        if (gen_type == 'solar'):
            config = {
                'module': 'simplemureilmaster_solar',
                'capex': 50,
                'size': 50,
                'install': 1000
            }
        elif (gen_type == 'wind'):
            config = {
                'module': 'simplemureilmaster_wind',
                'capex': 3,
                'wind_turbine': 2.5,
                'install': 500
            }
        elif (gen_type == 'gas'):
            config = {
                'module': 'simplemureilmaster_gas',
                'capex': 1.0,
                'price': 60,
                'carbon_tax': 20
            }
        
        return config

    
    def run(self):
        if (not self.is_configured):
            print 'simplemureilmaster is not configured'
            return None
    
        for i in range(self.config['iterations']):
            self.algorithm.do_iteration()
            
        self.after(self.algorithm.get_final())
        self.algorithm.tidy_up()
    
        return None
    
    
    def before(self, population):
        """input: None
        output: None
        prints values, scores, ect. at beginning
        """
        num = 0
        sum = 0
        for gene in population.genes:
            num += 1
            sum += gene.score
        print 'average score before:', float(sum)/num
        return None

    def after(self, input_data):
        """input: None
        output: None
        prints values, scores, ect. at end
        """
        
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
        print 'best gene was: %s' % str(optim[0])
        print 'on loop %i, with score %f' % (optim[2], optim[1])
        for data in clones_data:
            if data[1] > optim[1]:
                optim = data
        print '%i nuke/s dropped' % len(clones_data)
        print 'average score after:', float(sum)/num   

        pickle.dump(best_gene_data, open(self.config['output_file'], "wb"))
        
        return None

    def elec_calc(self, params):   
        icount=0
        elec=np.zeros(self.nsteps)
        elec_solar=np.zeros(self.nsteps)
        elec_wind=np.zeros(self.nsteps)


        for i in range(self.nsolar_stats):
            elec_solar += self.ts_solar[:,i] * params[icount] * self.solar['size'] #ts_solar should already be in units of capacity
            icount += 1
        for i in range(self.nwind_stats):
            elec_wind += self.ts_wind[:,i] * params[icount] / 1000.0
            icount += 1

        elec = elec_wind + elec_solar
        return elec

    def calc_cost(self, gene, elec):

        params=np.array(gene)

        if self.config['optim_type'] == 'match_demand':
            cost = abs(self.ts_demand-elec).sum()/1000.0  #now in GW

        if self.config['optim_type'] == 'missed_supply':

            switch_variable = self.config['cost_calc']

            if (switch_variable == 'basic'):
                cost_solar = params[0:self.nsolar_stats].sum()*self.solar['capex']
                cost_wind = params[self.nsolar_stats:self.nsolar_stats + self.nwind_stats].sum()*self.wind['capex']

            elif (switch_variable == 'linear_install'):
                cost_temp=np.zeros(self.nsolar_stats)
                for i in range(self.nsolar_stats):
                    if params[i] < 1:
                        cost_temp[i]=0
                    else:
                        cost_temp[i]=self.solar['install']+(params[i]*self.solar['capex'])
                cost_solar=cost_temp.sum()

                turb_count=self.nsolar_stats
                cost_temp=np.zeros(self.nwind_stats)
                for i in range(self.nwind_stats):
                    if params[turb_count] < 1:
                        cost_temp[i]=0
                    else:
                        cost_temp[i]=self.wind['install']+(params[turb_count]*self.wind['capex'])
                    turb_count+=1
                cost_wind=cost_temp.sum()

            elif (switch_variable == 'exponential_install'):
                cost_temp=np.zeros(self.nsolar_stats)
                for i in range(self.nsolar_stats):
                    if params[i] < 1:
                        cost_temp[i]=0
                    else:
                        cpt = ((self.solar['install'] - self.solar['capex']) *
                               np.exp(-0.1 * (params[i] - 1))) + self.solar['capex']
                        cost_temp[i] = params[i] * cpt
                cost_solar=cost_temp.sum()

                turb_count = self.nsolar_stats
                cost_temp=np.zeros(self.nwind_stats)
                for i in range(self.nwind_stats):
                    if params[turb_count] < 1:
                        cost_temp[i]=0
                    else:
                        cpt = ((self.wind['install'] - self.wind['capex']) *
                               np.exp(-0.1 * (params[turb_count] - 1))) + self.wind['capex']
                        cost_temp[i] = params[turb_count] * cpt
                    turb_count+=1
                cost_wind=cost_temp.sum()

            (hydro_cost, hydro_ts, elec) = self.hydro.calculate_operation(self.ts_demand, elec)

            gas = self.gas_elec(elec)
            gas_cost = gas[0]
            elec = gas[1]

            ineg = (self.ts_demand - elec) > 0
            if ineg.any():
                cost_failedsupply = float((self.ts_demand[ineg] - elec[ineg]).sum())/200
            else:
                cost_failedsupply = 0.0

            cost = cost_failedsupply + cost_wind + cost_solar + hydro_cost + gas_cost
        #pdb.set_trace()
        return cost


    def gas_elec(self, elec):

        conf = self.gas

        diff = self.ts_demand - elec
        ii = (diff > 0)
        if ii.any():
            gas_cap = diff[ii].max() / 1000.0
            gas_cost_I = diff[ii].sum() / 2.0 * (conf['price'] + conf['carbon_tax'])/1000.0
            elec[ii] = self.ts_demand[ii]
        else:
            gas_cost_I = 0
            gas_cap = 0

        gas_cost = gas_cost_I + gas_cap * conf['capex'] * 1000.0

        return gas_cost,elec


    def gene_test(self, vals):
        """input: list
        output: float
        takes the gene.values, tests it and returns the genes score
        """
        elec = self.elec_calc(vals)
        score = -1 * self.calc_cost(vals,elec)
        return score
