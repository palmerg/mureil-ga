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
"""Performs a basic regression test on the 
directory provided. It checks simply that the
final results are in agreement, and if not, writes
both of the 'best_gene_data' structures out to the 
file diff.txt. The run log is at test.log.
This is written to be called from the test.py files
in the subdirectories.
"""

import sys
sys.path.append('..')
import os
import runmureil
import pickle
import pprint

def single_test(file_dir, config_name, pickle_name):

    cwd = os.getcwd()

    os.chdir(file_dir)

    config_file = config_name
    pickle_file = pickle_name
    new_pickle_file = 'test_out.pkl'
    new_log_file = 'test.log'
    new_diff_file = 'diff.txt'

    if os.path.isfile(new_pickle_file):
        os.remove(new_pickle_file)

    if os.path.isfile(new_log_file):
        os.remove(new_log_file)
    
    if os.path.isfile(new_diff_file):
        os.remove(new_diff_file)

    flags = ['-f', config_file,
        '--output_file', new_pickle_file, '-l',
        new_log_file, '-d', 'DEBUG']
        
    runmureil.runmureil(flags)    

    if os.path.isfile(new_pickle_file):
        exp_result = pickle.load(open(pickle_file, 'rb'))
        new_result = pickle.load(open(new_pickle_file, 'rb'))

        exp_bgd = exp_result['best_gene_data']
        new_bgd = new_result['best_gene_data']
    
        match = (exp_bgd == new_bgd)
    
        if not match:
            f = open(file_dir + '/' + 'diff.txt', 'w')
            pp = pprint.PrettyPrinter(indent=4, stream=f)
            f.write('Expected best gene data\n')
            f.write('=======================\n')
            pp.pprint(exp_bgd)
            f.write('This run best gene data\n')
            f.write('=======================\n')
            pp.pprint(new_bgd)
            f.close()
    else:
        match = False

    os.chdir(cwd)
    
    return match
    