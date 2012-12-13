"""Test of basicpumpedhydro

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_basicpumpedhydro.py
"""

import sys
sys.path.append('..')

import unittest
import numpy as np

import hydro.basicpumpedhydro

class TestBasicPumpedHydro(unittest.TestCase):
    def setUp(self):
        self.hydro = hydro.basicpumpedhydro.BasicPumpedHydro()

    def test_defaults(self):
        conf = self.hydro.get_config()
        expected_conf = {
            'capex': 2.0,
            'gen': 2000,
            'cap': 10000,
            'res': 5000,
            'water_factor': 0.01,
            'pump_round_trip': 0.8
        }
        self.assertEqual(conf, expected_conf)
        
    def test_flow(self):
        config = {
            'capex': 2.0,
            'gen': 2000,
            'cap': 10000,
            'res': 5000,
            'water_factor': 0.01,
            'pump_round_trip': 0.8
        }
        self.hydro.set_config(config)
        
        supply_need = np.array([50, 100, 100])
        
        #exp_ts = supply_need
        #exp_cost = max(exp_ts) * config['capex']
        
        # Same as above, but explicitly calculated by hand
        # Try setting 'gen' to 20 above instead of 2000 to see
        # how the errors appear
        exp_ts = np.array([50, 100, 100])
        exp_cost = 200
        
        (out_cost, out_ts) = self.hydro.calculate_cost_and_output([], supply_need)
        
        # The tolist thing is so that the numpy array (which basicpumpedhydro
        # expects) gets turned into a list, which is what unittest expects.
        self.assertListEqual(out_ts.tolist(), exp_ts.tolist())
        self.assertEqual(out_cost, exp_cost)
      
      
if __name__ == '__main__':
    unittest.main()
    