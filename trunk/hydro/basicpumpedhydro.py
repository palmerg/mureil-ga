"""Implements the BasicPumpedHydro class
"""

import tools.mureilbase as mureilbase
import numpy as np
import generator.singlepassgenerator as singlepassgenerator
import tools.mureilexception as mureilexception
import logging

logger = logging.getLogger(__name__)

class BasicPumpedHydro(singlepassgenerator.SinglePassGeneratorBase):
    """Class models a simple pumped hydro system that
       always pumps up when extra supply is available,
       and always releases when excess demand exists.
    """

    def set_config(self, config):
        singlepassgenerator.SinglePassGeneratorBase.set_config(self, config)
        
        # Check the pump_round_trip is <= 1
        if self.config['pump_round_trip'] > 1:
            msg = ('BasicPumpedHydro requires pump_round_trip to be less than 1. ' +
                ' Value = {:.3f}'.format(self.config['pump_round_trip']))
            logger.critical(msg) 
            raise mureilexception.ConfigException(msg, 
                'BasicPumpedHydro.set_config', {})

        # Pre-calculate these for improved speed
        # Instead of calculating explicitly the water that's pumped up, calculate
        # the amount of electricity that's stored.
        # Adjust here for the timestep - elec_res is in units of MW-timesteps.
        # so 1 MWh = (60/timestep) MW-timesteps
        self.elec_res = (1 / self.config['timestep_hrs']) * (
            float(self.config['starting_level']) / float(self.config['water_factor']))
        self.elec_cap = (1 / self.config['timestep_hrs']) * (
            float(self.config['dam_capacity']) / float(self.config['water_factor']))
        self.pump_round_trip_recip = 1 / self.config['pump_round_trip']


    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            capex: cost in $M per MW of capacity
            max_gen: max generator capacity, in MW
            ### TODO - should these be GL water?
            dam_capacity: dam capacity in ML
            starting_level: starting level in ML
            water_factor: translation of MWh to ML - 1 MWh requires water_factor ML water
            pump_round_trip: efficiency of pump up / draw down operation, a proportion
            timestep_hrs: float - the system timestep in hours
            min_param_val: integer - the minimum params value to handle
            max_param_val: integer - the maximum params value to handle
        """
        return [
            ('capex', float, None),
            ('max_gen', float, None),
            ('dam_capacity', float, None),
            ('starting_level', float, None),
            ('water_factor', float, None),
            ('pump_round_trip', float, 0.8),
            ('timestep_hrs', float, None)
            ]

       
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
        gen = self.config['max_gen']
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
            