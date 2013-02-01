#!/usr/bin/env python
print "Content-Type: text/json"
print
import rungedemo
from collections import defaultdict
import argparse
import json;

flags = ['-f', 'GEconfig.txt', '-l', 'GEConfig.log']

# file_path = 'new_values_to_model.js'
# 
# with open(file_path) as f:
#     input_data = f.read()

import cgi
form = cgi.FieldStorage()
input_data = form['sysdata'].value

all_years_out = rungedemo.rungedemo(flags, input_data)

print json.dumps(all_years_out);