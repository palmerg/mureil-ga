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
        self.ts_wind = f.variables['ts_wind'][:,:]

        infile = self.config['dir'] + self.config['solar']
        f = nc.NetCDFFile(infile)
        self.ts_solar = f.variables['ts_solar'][:,:]

        infile = self.config['dir'] + self.config['demand']
        f = nc.NetCDFFile(infile)
        self.ts_demand = f.variables['ts_demand'][:]
        
        return None


    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
        dir: full or relative path to file directory
        wind: filename of netCDF file with wind data, in ts_wind variable.
        solar: filename of netCDF file with solar data, in ts_solar variable.
        demand: filename of netCDF file with demand data, in ts_demand variable.
        """
        return [
            ('dir', None, './'),
            ('wind', None, None),
            ('solar', None, None),
            ('demand', None, None)
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
        
