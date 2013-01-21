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
"""Implements a Data class that reads in separate netCDF files for
   wind, solar and demand, on a single pass into an array.
"""

import pupynere as nc

import data.datasinglepassbase as datasinglepassbase

class Data(datasinglepassbase.DataSinglePassBase):
    """Read in separate netCDF files for wind, solar and demand.
       Return as whole arrays, on request.
    """
    
    def set_config(self, config):
        """Set the config, and read the files into memory.
        """
        datasinglepassbase.DataSinglePassBase.set_config(self, config)
        infile = self.config['dir'] + self.config['wind']
        f = nc.NetCDFFile(infile)
        self.ts_wind = f.variables[self.config['vbl_wind']][:,:]

        infile = self.config['dir'] + self.config['solar']
        f = nc.NetCDFFile(infile)
        self.ts_solar = f.variables[self.config['vbl_solar']][:,:]

        infile = self.config['dir'] + self.config['demand']
        f = nc.NetCDFFile(infile)
        self.ts_demand = f.variables[self.config['vbl_demand']][:]
        
        return None


    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
        dir: full or relative path to file directory
        wind: filename of netCDF file with wind data
        solar: filename of netCDF file with solar data
        demand: filename of netCDF file with demand data
        vbl_wind: variable name within netCDF for wind data. Defaults to ts_wind.
        vbl_solar: variable name within netCDF for solar data. Defaults to ts_solar.
        vbl_demand: variable name within netCDF for demand data. Defaults to ts_demand.
        """
        return [
            ('dir', None, './'),
            ('wind', None, None),
            ('solar', None, None),
            ('demand', None, None),
            ('vbl_wind', None, 'ts_wind'),
            ('vbl_solar', None, 'ts_solar'),
            ('vbl_demand', None, 'ts_demand')
            ]
        
    
    def wind_data(self):
        """Return the full wind timeseries as an array.
        """
        return self.ts_wind

    def solar_data(self):
        """Return the full solar timeseries as an array.
        """
        return self.ts_solar

    def demand_data(self):
        """Return the full demand timeseries as an array.
        """
        return self.ts_demand
        
