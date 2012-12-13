import generator.singlepassgenerator as singlepassgenerator
import numpy

class LinearMissedSupply(singlepassgenerator.SinglePassGeneratorBase):
    """Missed supply model charging a flat rate per
    MW missed.
    """
    
    def get_default_config(self):
        """Params: 
            cost_per_mw - the cost, in $M, for each MW of
                supply missed, at the given timestep.
        """
        return {'cost_per_mw': 0.005}

    
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Meets all remaining demand by pricing the missed supply
        penalty.
        
        Inputs:
            params: ignored
            rem_demand: numpy.array - a time series of the demand remaining
                to be met.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.

        Outputs:
            cost: number - sum of 'output' times configured cost_per_mw. 
            output: numpy.array - Power 'generated' at each timestep,
                simply rem_demand where > 0.
        """
        output = rem_demand.clip(0)
        sum_out = numpy.sum(output)
        cost = sum_out * self.config['cost_per_mw']
        
        if save_result:
            self.saved['capacity'] = sum_out
            self.saved['output'] = numpy.copy(output)
            self.saved['cost'] = cost
            
        return cost, output


    def interpret_to_string(self):
        if self.saved:
            return 'Linear Missed-Supply, total {:.2f} MW-timestamps missed'.format(
                self.saved['capacity'])
        else:
            return None

            
class CappedMissedSupply(singlepassgenerator.SinglePassGeneratorBase):
    """Missed supply model charging a flat rate per
    MW missed, and a penalty for going over a total limit.
    """
    
    def get_default_config(self):
        """Params: 
            cost_per_mw - the cost, in $M, for each MW of
                supply missed, at the given timestep.
            reliability_reqt - a percentage of total system demand
                that can be missed before penalty applies.
            penalty - the cost of exceeding reliability_reqt missed.
        """
        return {'cost_per_mw': 0.005, 'reliability_reqt': 0.002,
            'penalty': 1e10}

    
    def get_data_types(self):
        return ['ts_demand']

        
    def set_data(self, data):
        self.total_demand = sum(data['ts_demand'])
        
    
    def calculate_cost_and_output(self, params, rem_demand, save_result=False):
        """Meets all remaining demand by pricing the missed supply
        penalty per MW-timestep, with additional penalty for exceeding 
        average reliability limit over time period.
        
        Inputs:
            params: ignored
            rem_demand: numpy.array - a time series of the demand remaining
                to be met.
            save_result: boolean, default False - if set, save the results
                from these params and rem_demand into the self.saved dict.

        Outputs:
            cost: number - sum of 'output' times configured cost_per_mw,
                plus configured penalty if total output / total demand 
                > reliability_reqt. 
            output: numpy.array - Power 'generated' at each timestep,
                simply rem_demand where > 0.
        """
        output = rem_demand.clip(0)
        sum_out = numpy.sum(output)

        cost = sum_out * self.config['cost_per_mw']
        
        # unreliability as a percentage
        unreliability = sum_out / self.total_demand * 100.0
        
        if (unreliability > self.config['reliability_reqt']): 
            cost += self.config['penalty']

        if save_result:
            self.saved['capacity'] = sum_out
            self.saved['output'] = numpy.copy(output)
            self.saved['cost'] = cost
            self.saved['other'] = {'unreliability': unreliability}
            
        return cost, output


    def interpret_to_string(self):
        if self.saved:
            return 'Capped Missed-Supply, total {:.2f} MW-timestamps missed, unreliability {:.3f}%'.format(
                self.saved['capacity'], self.saved['other']['unreliability'])
        else:
            return None