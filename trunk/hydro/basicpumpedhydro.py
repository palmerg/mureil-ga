"""Implements the BasicPumpedHydro class
"""

import tools.mureilbase as mureilbase
import numpy as np
import generator.singlepassgenerator as singlepassgenerator

class BasicPumpedHydro(singlepassgenerator.SinglePassGeneratorBase):
    """Class models a simple pumped hydro system that
       always pumps up when extra supply is available,
       and always releases when excess demand exists.
    """

    def set_config(self, config):
        mureilbase.ConfigurableBase.set_config(self, config)
        # Pre-calculate these for improved speed
        # Instead of calculating explicitly the water that's pumped up, calculate
        # the amount of electricity that's stored.
        self.elec_res = float(self.config['res']) / float(self.config['water_factor'])
        self.elec_cap = float(self.config['cap']) / float(self.config['water_factor'])
        self.pump_round_trip_recip = 1 / self.config['pump_round_trip']


    def get_default_config(self):
        """Configuration:
        *** TODO - correct these
        capex: cost per ?
        gen: max generator capacity
        cap: dam capacity in ML (?)
        res: starting level
        water_factor: translation ML to MW (?)
        pump_round_trip: efficiency of pump up / draw down operation
        """
        config = {
            'capex': 2.0,
            'gen': 2000,
            'cap': 10000,
            'res': 5000,
            'water_factor': 0.01,
            'pump_round_trip': 0.8
        }

        return config
       
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Calculate the time series of electricity in and out for the
        pumped hydro.
        
        Input parameters:
            params: ignored
            rem_demand: numpy.array - a time series of the demand remaining
                to be met. May have negatives indicating excess power available.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
        
        Returns:
            cost: number - capex for maximum generator capacity used 
            output: numpy.array - Power generated at each timestep, or
                negative if power consumed.
        """
        output = np.zeros(len(rem_demand))
        elec_res_temp = self.elec_res
        gen = self.config['gen']
        elec_cap = self.elec_cap
        pump_round_trip = self.config['pump_round_trip']
        pump_round_trip_recip = self.pump_round_trip_recip
        
        for i in range(len(rem_demand)):
            elec_diff = rem_demand[i]
            if elec_diff > 0:
                elec_to_release = elec_diff
                if elec_to_release > gen:
                    elec_to_release = gen
                if elec_to_release > elec_res_temp:
                    elec_to_release = elec_res_temp
                    elec_res_temp = 0
                else:
                    elec_res_temp -= elec_to_release
                output[i] = elec_to_release
            else:
                elec_to_store = -elec_diff
                if elec_to_store > gen:
                    elec_to_store = gen
                elec_to_store *= pump_round_trip
                if elec_to_store > elec_cap - elec_res_temp:
                    elec_to_store = elec_cap - elec_res_temp
                    elec_res_temp = elec_cap
                else:
                    elec_res_temp += elec_to_store
                elec_used = elec_to_store * pump_round_trip_recip
                output[i] = -elec_used

        hydro_max = np.max(np.abs(output))
        cost = hydro_max * self.config['capex']
        
        if save_result:
            self.saved['capacity'] = hydro_max
            self.saved['output'] = np.copy(output)
            self.saved['cost'] = cost
         
        return cost, output


    def interpret_to_string(self):
        if self.saved:
            return 'Basic Pumped Hydro, maximum generation capacity (MW) {:.2f}'.format(
                self.saved['capacity'])
        else:
            return None
            