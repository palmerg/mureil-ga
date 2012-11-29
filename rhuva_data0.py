# Based on Robert's case0
import pupynere as nc

class Data:
    def __init__(self, config):
        dir = './'
        file = 'CoV_output.nc'
        infile = dir + file
        f = nc.NetCDFFile(infile)
        self.ts_wind = f.variables['ts_wind'][:,:]
        self.ts_solar = f.variables['ts_solar'][:,:]
        self.ts_demand = f.variables['ts_demand'][:]
        return None

    def wind_data(self):
        return self.ts_wind


    def solar_data(self):
        return self.ts_solar


    def demand_data(self):
        return self.ts_demand
        
