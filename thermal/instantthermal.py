import generator.singlepassgenerator as singlepassgenerator
import numpy

class InstantMaxThermal(singlepassgenerator.SinglePassGeneratorBase):
    """A fossil thermal generator, that instantly matches demand,
    and determines maximum size required.
    """
    
    def get_default_config(self):
        """Params: 
            capex - ? ## TODO - clarify the units here asap
            price - ?
            carbon_tax - ?
        """
        return {
            'capex': 1.0,
            'price': 60,
            'carbon_tax': 20
        }
        
        
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

        ## TODO - clarify all the units here asap. And why the divide-by-2
        ## on the gas cost?

        output = rem_demand.clip(0)
        max_cap = numpy.max(output)
        variable_cost = numpy.sum(output) * (self.config['price'] + 
            self.config['carbon_tax']) / (2.0 * 1000.0)
        cost = variable_cost + self.config['capex'] * max_cap
        
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
     
     def get_default_config(self):
         """Params: 
             capex - ? ## TODO - clarify the units here asap
             price - ?
             carbon_tax - ?
         """
         return {
             'capex': 1.0,
             'price': 60,
             'carbon_tax': 20
         }
         
      
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
 
         ## TODO - clarify all the units here asap. And why the divide-by-2
         ## on the gas cost?
 
         max_cap = params[0] * 100
         # numpy.clip sets lower and upper bounds on array values
         output = rem_demand.clip(0, max_cap)
         variable_cost = numpy.sum(output) * (self.config['price'] + 
             self.config['carbon_tax']) / (2.0 * 1000.0)
         cost = variable_cost + self.config['capex'] * max_cap
         
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
            