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
# Based on Robert's case1
import pupynere as nc

import data.datasinglepassbase as datasinglepassbase

class Data(datasinglepassbase.DataSinglePassBase):
    def set_config(self, config):
        datasinglepassbase.DataSinglePassBase.set_config(self, config)
        dir = '../access_2month_optim/'
        file = 'CoV_wind_station_output_prox_penalty.nc' #file with _II has smaller exclusion zone
        infile = dir + file
        f = nc.NetCDFFile(infile)
        self.ts_wind = f.variables['CoV_wind'][:,:]

        file = 'CoV_dsr_station_output_prox_penalty.nc'
        infile = dir + file
        f = nc.NetCDFFile(infile)
        self.ts_solar = f.variables['CoV_dsr'][:,:]

        file = 'Aus_demand_sample_raw.nc'
        infile = dir + file
        f = nc.NetCDFFile(infile)
        self.ts_demand = f.variables['ts_demand'][:]
        
        return None

    def wind_data(self):
        return self.ts_wind

    def solar_data(self):
        return self.ts_solar

    def demand_data(self):
        return self.ts_demand
        
