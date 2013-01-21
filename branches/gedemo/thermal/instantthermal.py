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
import generator.singlepassgenerator as singlepassgenerator
import numpy

class InstantMaxThermal(singlepassgenerator.SinglePassGeneratorBase):
    """A fossil thermal generator, that instantly matches demand,
    and determines maximum size required.
    """
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)
        
        Configuration:
            capex: float - Cost in $M per MW of capacity installed
            fuel_price_mwh: float - Cost in $ per MWh generated
            carbon_price: float - Cost in $ per Tonne
            carbon_intensity: float - in kg/kWh or equivalently T/MWh
            timestep_hrs: float - the system timestep in hours
            variable_cost_mult: float - the value to multiply the calculated variable
                cost by, to account for a shorter dataset than the capex lifetime.
        """
        return [
            ('capex', float, None),
            ('fuel_price_mwh', float, None),
            ('carbon_price', float, None),
            ('carbon_intensity', float, None),
            ('timestep_hrs', float, None),
            ('variable_cost_mult', float, None)
            ]
      
        
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Meets all remaining demand by burning fossil fuel, and
        builds whatever capacity is needed to do so.
        
        Inputs:
            params: ignored
            rem_demand: numpy.array - a time series of the demand remaining
                to be met.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.
        Outputs:
            cost: number - capex cost plus fuel and carbon tax cost. 
            output: numpy.array - Power generated at each timestep.
        """

        output = rem_demand.clip(0)
        max_cap = numpy.max(output)
        # price and carbon_tax are in $/MWh
        variable_cost = numpy.sum(output) * self.config['timestep_hrs'] * (
            self.config['fuel_price_mwh'] + (
            self.config['carbon_price'] * self.config['carbon_intensity'])) / float(1e6)
        cost = variable_cost * self.config['variable_cost_mult'] + self.config['capex'] * max_cap
        
        if save_result:
            self.saved['capacity'] = max_cap
            self.saved['cost'] = cost
            self.saved['output'] = numpy.copy(output)

        return cost, output
        

    def interpret_to_string(self):
        if self.saved:
            return 'Instant Fossil Thermal, max capacity (MW) {:.2f}'.format(
                self.saved['capacity'])
        else:
            return None
 
 
class InstantOptimisableThermal(singlepassgenerator.SinglePassGeneratorBase):
    """A fossil thermal generator, that instantly matches demand,
    with capacity determined by the optimiser.
    """

    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)
        
        Configuration:
            capex: float - Cost in $M per MW of capacity installed
            fuel_price_mwh: float - Cost in $ per MWh generated
            carbon_price: float - Cost in $ per Tonne
            carbon_intensity: float - in kg/kWh or equivalently T/MWh
            timestep_hrs: float - the system timestep in hours
            variable_cost_mult: float - the value to multiply the calculated variable
                cost by, to account for a shorter dataset than the capex lifetime.
        """
        return [
            ('capex', float, None),
            ('fuel_price_mwh', float, None),
            ('carbon_price', float, None),
            ('carbon_intensity', float, None),
            ('timestep_hrs', float, None),
            ('variable_cost_mult', float, None)
            ]

    def get_param_count(self):
        """Ask for 1 parameter to specify the capacity of fossil to build.
        """
        return 1
    
    
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Attempts to meet remaining demand by burning fossil fuel, and
        builds capacity as directed by its params.
        
        Inputs:
            params: specifies capacity
            rem_demand: numpy.array - a time series of the demand remaining
                 to be met.
            save_result: boolean, default False - if set, save the results
                 from these params and rem_demand into the self.saved dict.
         Outputs:
            cost: number - capex cost plus fuel and carbon tax cost. 
             output: numpy.array - Power generated at each timestep.
         """
 
        max_cap = params[0] * 100
        # numpy.clip sets lower and upper bounds on array values
        output = rem_demand.clip(0, max_cap)
        variable_cost = numpy.sum(output) * self.config['timestep_hrs'] * (
            self.config['fuel_price_mwh'] + (
            self.config['carbon_price'] * self.config['carbon_intensity'])) / 1e6
        cost = variable_cost * self.config['variable_cost_mult'] + self.config['capex'] * max_cap
        
        if save_result:
            self.saved['capacity'] = max_cap
            self.saved['cost'] = cost
            self.saved['output'] = numpy.copy(output)
 
        return cost, output
         
 
    def interpret_to_string(self):
        if self.saved:
            return 'Instant Fossil Thermal, optimisable, max capacity (MW) {:.2f}'.format(
                self.saved['capacity'])
        else:
            return None
            