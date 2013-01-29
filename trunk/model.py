#!/usr/bin/env python
print "Content-Type: text/json"
print
import runmureil
from collections import defaultdict
import argparse
import json;

year_list = [2010, 2020, 2030, 2040, 2050]


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

print json.dumps(json_out);