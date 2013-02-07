#
#
# Copyright (C) University of Melbourne 2012
#
#
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#
#
"""Functions for use in testbench operation.
"""

import os
from tools import mureilbuilder

def unittest_path_setup(self, thisfile):
    """Set up all the paths to run the unit tests. Required when using
    unittest discover.
    
    Determines the directory the test itself is in, and the
    directory it is being called from. Changes into the test directory
    to run the test. Sets the cwd variable in self to the working directory.
    
    Also resets the logger functionality, sending output to stdout.
    
    Inputs:
        self: the unittest.TestCase object calling this function
            (specific object type is irrelevant - just needs to be an object)
        thisfile: the __file__ value for the test module
    
    Outputs:
        None
    """
    
    test_dir = os.path.dirname(os.path.realpath(thisfile)) 
    self.cwd = os.getcwd()
    os.chdir(test_dir)
    mureilbuilder.do_logger_setup({})
