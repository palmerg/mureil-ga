"""Regression test.
rhuva_test1 - an early test from Robert
"""

#################################
#### PUT YOUR FILENAMES HERE ####
#################################

config = 'sample_config.txt'
pickle = 'mureil_sample.pkl'

import sys
sys.path.append('../..')

import os
test_dir = os.path.dirname(os.path.realpath(__file__)) 

import unittest
from test_regression.single_test import single_test

class RegressionTest(unittest.TestCase):
    def test(self):
        self.assertTrue(single_test(
            test_dir, config, pickle))
      
if __name__ == '__main__':
    unittest.main()
    