"""Test of slowresponsethermal

   Using the Python unittest library: 
   http://docs.python.org/2/library/unittest.html#
   
   To run it, at a command line:
   python test_slowresponsethermal.py
"""

import sys
sys.path.append('..')

import os

import unittest
import numpy as np
import tools.mureilexception as mureilexception
import logging

import thermal.slowresponsethermal

class TestSlowResponseThermal(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.thermal = thermal.slowresponsethermal.SlowResponseThermal()
        test_dir = os.path.dirname(os.path.realpath(__file__)) 
        self.cwd = os.getcwd()
        os.chdir(test_dir)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_simple(self):
        config = {
            'capex': 3.0,
            'fuel_price_mwh': 10,
            'carbon_price': 5,
            'carbon_intensity': 1.0,
            'timestep_hrs': 1.0,
            'variable_cost_mult': 1.0,
            'ramp_time_mins': 240,
            'type': 'BlackCoal'
        }

        ts_demand = {'ts_demand': np.array([110, 120, 130, 140, 140, 140, 140, 130, 120, 110])}
        rem_demand = np.array([10, 20, 30, 40, 40, 40, 40, 30, 20, 10])
        
        # for original no-code version, just output at full capacity all the time
        # will test here with capacity = 500MW
        exp_ts = np.array([500, 500, 500, 500, 500, 500, 500, 500, 500, 500])
        exp_cost = (10 * 500 * (10 + 5)) * 1e-6 + (3 * 500)
        
        try:
            self.thermal.set_config(config)
            self.thermal.set_data(ts_demand)
            # param is multiplied by 100 to give capacity in MW, so '5' is used here.
            (out_cost, out_ts) = self.thermal.calculate_cost_and_output([5], rem_demand)
            print out_cost
            print out_ts
        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    
        
        # The tolist thing is so that the numpy array (which basicpumpedhydro
        # expects) gets turned into a list, which is what unittest expects.

        self.assertListEqual(out_ts.tolist(), exp_ts.tolist())
        self.assertEqual(out_cost, exp_cost)
    

class TestSlowResponseThermalFixed(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.thermal = thermal.slowresponsethermal.SlowResponseThermalFixed()
        test_dir = os.path.dirname(os.path.realpath(__file__)) 
        self.cwd = os.getcwd()
        os.chdir(test_dir)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_simple(self):
        config = {
            'capex': 3.0,
            'fuel_price_mwh': 10,
            'carbon_price': 5,
            'carbon_intensity': 1.0,
            'timestep_hrs': 1.0,
            'variable_cost_mult': 1.0,
            'ramp_time_mins': 240,
            'type': 'BlackCoal',
            'fixed_capacity': 1200
        }

        ts_demand = {'ts_demand': np.array([110, 120, 130, 140, 140, 140, 140, 130, 120, 110])}
        rem_demand = np.array([10, 20, 30, 40, 40, 40, 40, 30, 20, 10])
        
        # for original no-code version, just output at full capacity all the time
        # will test here with capacity = 1200 MW
        exp_ts = np.array([1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200])
        exp_cost = (10 * 1200 * (10 + 5)) * 1e-6 + (3 * 1200)
        
        try:
            self.thermal.set_config(config)
            self.thermal.set_data(ts_demand)
            (out_cost, out_ts) = self.thermal.calculate_cost_and_output([], rem_demand)
            print out_cost
            print out_ts
        except mureilexception.MureilException as me:
            print me.msg
            self.assertEqual(False, True)    
        
        # The tolist thing is so that the numpy array (which basicpumpedhydro
        # expects) gets turned into a list, which is what unittest expects.

        self.assertListEqual(out_ts.tolist(), exp_ts.tolist())
        self.assertEqual(out_cost, exp_cost)
    

      
if __name__ == '__main__':
    unittest.main()
    
