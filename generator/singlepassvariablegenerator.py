import tools.mureilbase as mureilbase
import string
import numpy
import generator.singlepassgenerator as singlepassgenerator

class VariableGeneratorBasic(singlepassgenerator.SinglePassGeneratorBase):
    """Implement a basic model for variable generation that uses
    capacity factor time series to determine output, and calculates
    cost as a multiple of capacity. Capacity is determined by
    optimisable parameters.
    """
    
    def get_default_config(self):
        """Params:
            capex - the cost in $M for 'size' of capacity
            size - the size in MW of plant for each unit of param
            type - a string name for the type of generator modelled
            data_type - a string key for the data required from the master for
                the set_data method.
        """
        return {
            'capex': 50,
            'size': 50,
            'type': 'solar_pv',
            'data_type': 'ts_solar'
        }

    
    def get_data_types(self):
        """Return a list of keys for each type of
        data required, for example ts_wind, ts_demand.
        
        Outputs:
            data_type: list of strings - each a key name 
                describing the data required for this generator.
        """
        
        return [self.config['data_type']]
        
        
    def set_data(self, data):
        """Set the data dict with the data series required
        for the generator.
        
        Inputs:
            data: dict - with keys matching those requested by
                get_data_types. 
        """
        self.ts_cap_fac = data[self.config['data_type']]
        
        
    def get_param_count(self):
        """Return the number of parameters that this generator,
        as configured, requires to be optimised. Returns
        the number of series in the ts_cap_fac array, as
        configured by set_data.
        
        Outputs:
            param_count: non-negative integer - the number of
                parameters required.
        """
        ## TODO - check that this is set up
        return self.ts_cap_fac.shape[1] 
        
        
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
                and operation. This generator simply multiplies the capacity
                by a unit cost.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the params, and the capacity factor data.
        """
        output = numpy.dot(self.ts_cap_fac, params) * self.config['size']
        cost = numpy.sum(params) * self.config['capex']

        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = params * self.config['size']
                
        return cost, output
    
    
    def interpret_to_string(self):
        """Return a string that describes the generator type and the
        current capacity, following a call to calculate_cost_and_output
        with set_current set.
        """
        return self.config['type'] + ' with capacities (MW): ' + (
            string.join(map('{:.2f} '.format, self.saved['capacity'])))
        
        
class VariableGeneratorLinearInstall(VariableGeneratorBasic):
    """Override the VariableGeneratorBasic calculate method by calculating an
    installation cost as well as capacity cost.
    """
    
    def get_default_config(self):
        """Params:
            as for VariableGeneratorBasic, with the addition of:
            install: number, the flagfall for a site.
        """
        config = VariableGeneratorBasic.get_default_config(self)
        config['install'] = 1000
        return config
    
    
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
                and operation. This generator simply multiplies the capacity
                by a unit cost.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the params, and the capacity factor data.
        """

        output = numpy.dot(self.ts_cap_fac, params) * self.config['size']
        active_sites = params[params > 0]
        cost = numpy.sum(active_sites) * self.config['capex'] + (
            self.config['install'] * active_sites.size)

        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = params * self.config['size']
                
        return cost, output


class VariableGeneratorExpCost(VariableGeneratorBasic):
    """Override the VariableGeneratorBasic calculate method by calculating an
    exponential method capacity cost.
    """
    
    def get_default_config(self):
        """Params:
            as for VariableGeneratorBasic, with the addition of:
            install: number, the flagfall for a site.
        """
        config = VariableGeneratorBasic.get_default_config(self)
        config['install'] = 1000
        return config
    
    
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
                and operation, calculated using an exponential function.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the params, and the capacity factor data.
        """

        output = numpy.dot(self.ts_cap_fac, params) * self.config['size']

        cost_temp = numpy.zeros(params.size)
        for i in range(params.size):
            if params[i] < 1:
                cost_temp[i] = 0
            else:
                cpt = ((self.config['install'] - self.config['capex']) *
                       numpy.exp(-0.1 * (params[i] - 1))) + self.config['capex']
                cost_temp[i] = params[i] * cpt
        cost = cost_temp.sum()

        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = params * self.config['size']
                
        return cost, output
                

class VariableGeneratorSqrtCost(VariableGeneratorBasic):
    """Override the VariableGeneratorBasic calculate method by calculating an
    square-root method capacity cost.
    """
    
    def get_default_config(self):
        """Params:
            as for VariableGeneratorBasic, with the addition of:
            install: number, the flagfall for a site.
            max_count: number, the maximum number of units installed, for
                cost calculation reference.
        """
        config = VariableGeneratorBasic.get_default_config(self)
        config['install'] = 1000
        config['max_count'] = 150
        return config
    
    
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
                and operation, calculated using a square-root function.
            output: numpy.array - a time series of the power output in MW
                from this generator, calculated as a product of the capacity,
                determined by the params, and the capacity factor data.
        """

        output = numpy.dot(self.ts_cap_fac, params) * self.config['size']

        cost_temp = numpy.zeros(params.size)
        m_gen = (self.config['capex'] * self.config['max_count']) / numpy.sqrt(self.config['max_count'])
        gen_add = self.config['install'] + self.config['capex'] - m_gen
        for i in range(params.size):
            if params[i] < 1:
                cost_temp[i] = 0
            else:
                cost_temp[i] = m_gen * numpy.sqrt(params[i]) + gen_add
        cost = cost_temp.sum()

        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = params * self.config['size']
                
        return cost, output
                