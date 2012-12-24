"""Regression test.
mg_test1 - a short test using sample data of early
code.
"""

#################################
#### PUT YOUR FILENAMES HERE ####
#################################

config = 'asst5_config.txt'
pickle = 'asst5.pkl'

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
    