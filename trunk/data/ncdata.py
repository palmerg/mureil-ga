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

"""Implements a Data class that reads in a list of variables from
   netCDF files, on a single pass into an array.
"""

import pupynere as nc

from data import datasinglepassbase
from tools import mureilbuilder

import copy

class Data(datasinglepassbase.DataSinglePassBase):
    """Read in a list of variables from netCDF files.
    """

    def process_initial_config(self):
        for ts_name in self.config['ts_list']:
            self.config_spec += [(ts_name + '_vbl', None, ts_name)]
            self.config_spec += [(ts_name + '_file', None, None)]


    # could optimise by opening the file only once
    # and need to check that all the required names are here - 
    # don't want to check them in base set_config above, but
    # want to use the set_config tricks to convert all the others.
    def complete_configuration(self):
        self.data = {}

        for ts_name in self.config['ts_list']:        
            infile = self.config['dir'] + self.config[ts_name + '_file']
            
            f = nc.NetCDFFile(infile)
            
            vbl = f.variables[self.config[ts_name + '_vbl']]
            dims = len(vbl.shape)
            
            if (dims == 1):
                self.data[ts_name] = vbl[:]
            else:
                self.data[ts_name] = vbl[:,:]

        self.ts_length = self.data[self.data.keys()[0]].shape[0]

        self.is_configured = True

        return None


    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
        dir: full or relative path to file directory
        ts_list: list of names of output ts - e.g. ts_wind, ts_solar
        
        then for each name in ts_list, e.g. ts_wind:
        ts_wind_file: filename of netCDF file with wind data
        ts_wind_vbl: optional - the name of the variable within the netCDF file. Defaults to 
            the timeseries name, here ts_wind.
        """
        return [
            ('dir', None, './'),
            ('ts_list', mureilbuilder.make_string_list, [])
            ]
        
