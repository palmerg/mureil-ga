# Based on Robert's case1
import pupynere as nc

import mureilbase

class Data(mureilbase.Mureilbase):
    def set_config(self, config):
        dir = './'
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

    def get_default_config(self):
        config = {
            'module' : 'rhuva_data1',
            'class' : 'Data'
        }
        
        return config

    def wind_data(self):
        return self.ts_wind

    def solar_data(self):
        return self.ts_solar

    def demand_data(self):
        return self.ts_demand
        
