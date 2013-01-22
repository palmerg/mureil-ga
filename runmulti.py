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
import runmureil
from collections import defaultdict
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--out_file', dest='out_file', default=None)
args = parser.parse_args()

# Example script that generates a batch of
# config files, to run with asst5_config.txt, and
# then runs them.

#solar_cost_list = [1, 2, 3]
year_list = [2010,2020,2030,2040,2050]

# Create the config files
#for solar_cost in solar_cost_list:
#    filename = 'solar_{:d}_config.txt'.format(solar_cost)
#    f = open(filename, 'w')
#    f.write('[Solar]\n')
#    f.write('capex: {:d}\n'.format(solar_cost))
#    f.write('[Master]\n')
#    f.write('output_file: solar_{:d}.pkl\n'.format(solar_cost))
#    f.close()

for runyear in year_list:
    filename = 'runyear_{:d}_config.txt'.format(runyear)
    f = open(filename, 'w')
    f.write('[Algorithm]\n')
    f.write('runyear: {:d}\n'.format(runyear))
    f.write('[Master]\n')
    f.write('output_file: runyear_{:d}.pkl\n'.format(runyear))
    f.close()

# Run the sims
#for solar_cost in solar_cost_list:
#    filename = 'solar_{:d}_config.txt'.format(solar_cost)
#    logname = 'solar_{:d}.log'.format(solar_cost)
#    runmureil.runmureil(['-f', 'GEconfig.txt', '-f', filename, '-l', logname,
#        '--iterations', '1'])

json_out = defaultdict(dict)
for runyear in year_list:
    
    result = runmureil.runmureil(['-f', 'GEconfig.txt', 
                         '-l', 'GEConfig.log', 
                         '--iterations', '1', 
                         '--run_year', str(runyear),])
    
    json_out[str(runyear)] = year_out = defaultdict(dict)
    year_out['output'] = output_section = defaultdict(dict)
    year_out['cost'] = cost_section = defaultdict(dict)
    
    for generator_type, values in result['best_results']['output']:
        output_section[generator_type] = str(sum(values))
    
    for generator_type, value in result['best_results']['cost']:
        cost_section[generator_type] = value
      
if args.out_file:
    import json
    print 'writing json to %s' % args.out_file  
    with open(args.out_file, 'w') as f:
        json.dump(json_out, f)
    


# Collect the results
#for runyear in year_list:
#    pkl_name = 'runyear_{:d}.pkl'.format(runyear)
#    p = pickle.load(open(pkl_name, 'rb'))
#    costs = p['best_results']['cost']
#    total_cost = sum([pair[1] for pair in costs])
#    capacities = p['best_results']['capacity']
#    
#    print '=========================================='
#    print 'Year = {:d}'.format(runyear)
#    print 'Total Cost $M = {:.2f}'.format(total_cost)
#    print 'Capacities:'
#    print capacities
    
