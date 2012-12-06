"""Implements the BasicPumpedHydro class
"""

import mureilbase
import numpy as np

class BasicPumpedHydro(mureilbase.Mureilbase):
    """Class models a simple pumped hydro system that
       always pumps up when extra supply is available,
       and always releases when excess demand exists.
    """

    def set_config(self, config):
        mureilbase.Mureilbase.set_config(self, config)
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
       
    def calculate_operation(self, supply_need):
        """Calculate the time series of electricity in and out for the
        pumped hydro.
        
        Input parameters:
        supply_need: time series of the difference between demand and supply.
                     May be positive or negative - negative indicates excess
                     power is available.
        
        Returns:
        hydro_cost: scalar capex for maximum generator capacity used
        hydro_ts: time series of electricity generation (-ve for consumption)
        """
        hydro_ts = np.zeros(len(supply_need))
        elec_res_temp = self.elec_res
        gen = self.config['gen']
        elec_cap = self.elec_cap
        pump_round_trip = self.config['pump_round_trip']
        pump_round_trip_recip = self.pump_round_trip_recip
        
        for i in range(len(supply_need)):
            elec_diff = supply_need[i]
            if elec_diff > 0:
                elec_to_release = elec_diff
                if elec_to_release > gen:
                    elec_to_release = gen
                if elec_to_release > elec_res_temp:
                    elec_to_release = elec_res_temp
                    elec_res_temp = 0
                else:
                    elec_res_temp -= elec_to_release
                hydro_ts[i] = elec_to_release
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
                hydro_ts[i] = -elec_used

        hydro_max = max(abs(hydro_ts))
        hydro_cost = hydro_max * self.config['capex']

        return hydro_cost, hydro_ts

    