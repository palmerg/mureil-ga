import numpy as np
import sys
sys.path.append('..')
import thermal.slowresponsethermal
config = {'capex': 3.0, 'fuel_price_mwh': 10, 'carbon_price': 5, 'carbon_intensity': 1.0, 'timestep_hrs': 1.0, 'variable_cost_mult': 1.0, 'ramp_time_mins': 240, 'type': 'bc'}
ts_demand = {'ts_demand': np.array([1, 2, 3])}
rem_demand = [3, 4, 5]
t = thermal.slowresponsethermal.SlowResponseThermal()
t.set_config(config)
t.set_data(ts_demand)
cost, ts = t.calculate_cost_and_output([5], rem_demand)
