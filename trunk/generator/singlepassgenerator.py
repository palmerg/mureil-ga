import tools.mureilbase as mureilbase

class SinglePassGeneratorBase(mureilbase.ConfigurableBase):
    """The base class for generic generators that calculate the
    output and cost based on the full timeseries in one pass. 
    """
    
    def __init__(self):
        """Do very basic initialisation of class members.
        Valid operation does not occur until all of the 'set'
        functions below, and set_config(), have been called.
        """
        mureilbase.ConfigurableBase.__init__(self)
        self.data = {}
        self.param_min = None
        self.param_max = None
        self.saved = {'capacity': None, 'output': None, 'cost': None, 'other': None}
        
    
    def get_data_types(self):
        """Return a list of keys for each type of
        data required, for example ts_wind, ts_demand.
        
        Outputs:
            data_type: list of strings - each a key name 
                describing the data required for this generator.
        """
        
        return []
        
        
    def set_data(self, data):
        """Set the data dict with the data series required
        for the generator.
        
        Inputs:
            data: dict - with keys matching those requested by
                get_data_types. 
        """
        self.data = data
        
        
    def get_param_count(self):
        """Return the number of parameters that this generator,
        as configured, requires to be optimised.
        
        Outputs:
            param_count: non-negative integer - the number of
                parameters required.
        """
        return 0
        
        
    def set_param_min_max(self, param_min, param_max):
        """Set the min and max parameter values that the 
        optimiser works within. The generator code is expected
        to scale within this as necessary.
        
        Inputs:
            param_min: number - minimum value params can take
            param_max: number - maximum value params can take
        """
        self.param_min = param_min
        self.param_max = param_max
        
        
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """From the params and remaining demand, update the current values, and calculate
        the output power provided and the total cost.
        
        Inputs:
            params: list of numbers - from the optimiser, with the list
                the same length as requested in get_param_count.
            rem_demand: numpy.array - a time series of the demand remaining
                to be met by this generator, or excess supply if negative.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
                
        Outputs:
            cost: number - total cost in $M of the generator capital
                and operation.
            output: numpy.array - a time series of the power output in MW
                from this generator.
        """
        return None
    
    
    def interpret_to_string(self):
        """Return a string that describes the generator type and the
        current capacity, following a call to calculate_cost_and_output
        with set_current set.
        """
        return None
        
        
    def get_saved_result(self):
        """Return a dict with capacity, output, cost and other, following a call
        to calculate_cost_and_output with save_result set.
        """
        return self.saved
        
    