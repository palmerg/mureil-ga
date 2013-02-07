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

import string
import numpy

from generator import singlepassgenerator

class VariableGeneratorBasic(singlepassgenerator.SinglePassGeneratorBase):
    """Implement a basic model for variable generation that uses
    capacity factor time series to determine output, and calculates
    cost as a multiple of capacity. Capacity is determined by
    optimisable parameters.
    """
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            capex - the cost in $M per MW capacity
            size - the size in MW of plant for each unit of param
            type - a string name for the type of generator modelled
            data_type - a string key for the data required from the master for
                the set_data method.
        """
        return [
            ('capex', float, None),
            ('size', float, None),
            ('type', None, None),
            ('data_type', None, None)
            ]

    
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
        cost = numpy.sum(params) * self.config['size'] * self.config['capex']

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
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            Same config as VariableGeneratorBasic, with the addition of:
            install: float, price in $M to build any plant.
        """        
        return VariableGeneratorBasic.get_config_spec(self) + [('install', float, None)]
    

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
        cost = numpy.sum(active_sites) * self.config['capex'] * self.config['size'] + (
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
    
    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            Same config as VariableGeneratorBasic, with the addition of:
            ### TODO - not yet fixed
            install: float, price in $M to build any plant.
        """        
        return VariableGeneratorBasic.get_config_spec(self) + [('install', float, None)]
    
    
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
                cpt = ((self.config['install'] - (self.config['size'] * self.config['capex'])) *
                       numpy.exp(-0.1 * (params[i] - 1))) + (
                        self.config['size'] * self.config['capex'])
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
            ### TODO - not yet fixed for units
    """
    
    def get_config_spec(self):
        return VariableGeneratorBasic.get_config_spec(self) + [('install', float, None),
            ('max_count', float, None)]

    
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
        gen_add = self.config['install'] + (
            self.config['size'] * self.config['capex']) - m_gen
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

class VariableGeneratorAsymptCost(VariableGeneratorBasic):
    """Override the VariableGeneratorBasic calculate method by using a
    method that has an asymptotic gradient for the capacity cost.
            ### TODO - not yet fixed for units
    """
    
    def get_config_spec(self):
        return VariableGeneratorBasic.get_config_spec(self) + [('install', float, None),
            ('max_count', float, None)]

    
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

        clipped = numpy.clip(params, 0, numpy.Inf)
        output = numpy.dot(self.ts_cap_fac, clipped) * self.config['size']

        cost_temp = numpy.zeros(params.size)
       
        alpha=0.2
        a=self.config['capex'] * self.config['size']

        for i in range(params.size):
            if params[i] < 1:
                cost_temp[i] = 0
            else:
                cost_temp[i] = self.config['install'] + (a * ((numpy.sqrt(a + (alpha * params[i])**2)) + (numpy.sqrt(a) * numpy.log(params[i])) - (numpy.sqrt(a) * numpy.log(a + numpy.sqrt(a) * numpy.sqrt(a + (alpha * params[i])**2)))) / alpha)
        cost = cost_temp.sum()


        distance_dict={'ts_solar':[  668730.4375   ,   909338.1875   ,   372287.25     ,
        1125613.25     ,   211878.890625 ,    68551.4609375,
         768108.3125   ,   513450.8125   ,  1239141.625    ,
         242710.109375 ,   221302.75     ,   835822.375    ,
         641565.125    ,  1371163.875    ,   404052.09375  ,
         449818.1875   ,   949940.75     ,  1176451.625    ,
        1239225.875    ,   811838.8125   ,   610120.125    ,
         679184.1875   ,  1126859.125    ,   926546.       ,
         987652.1875   ,  1093136.       ,   923490.5625   ,
         605613.3125   ,   681002.75     ,  1170811.375    ,
        1214910.625    ,   881211.1875   ,  1177105.25     ,
        1020829.875    ,   374478.46875  ,   884468.125    ,
        1147496.5      ,  1412441.       ,   557196.4375   ,
         111162.4375   ,  1129901.25     ,   901584.5625   ,
         207429.328125 ,   830748.625    ,  1097925.       ,
        1311133.125    ,   474638.53125  ,   231650.921875 ,
        1030239.5625   ,   784340.375    ,   599865.75     ,
         355621.71875  ,   801379.6875   ,  1050643.       ,
        1298696.375    ,   535831.75     ,  1012697.625    ,
         282052.       ,   738578.625    ,   468747.75     ,
         587530.1875   ,   874383.75     ,  1085080.5      ,
        1165477.5      ,   739965.6875   ,  1043011.9375   ,
         133451.609375 ,   466417.03125  ,   887445.1875   ,
         843954.375    ,   882972.9375   ,   911230.0625   ,
         256325.21875  ,   196988.21875  ,   722306.0625   ,
         494064.375    ,   656777.1875   ,   590096.75     ,
         838475.       ,   576432.125    ,  1038951.0625   ,
         709157.1875   ,   329522.5625   ,   246577.59375  ,
         866532.3125   ,   684706.0625   ,   507050.0625   ,
         353760.5      ,   528336.75     ,   308515.5      ,
         294442.8125   ,    38012.9140625,   354666.53125  ,
         473246.90625  ,   815155.4375   ,   729953.8125   ,
         211116.015625 ,   548792.25     ,   134444.53125  ,
         367146.65625  ,   252677.890625 ,   404498.71875  ,
         615562.1875   ,   426158.125    ,   478903.125    ,
         478492.6875   ,   204912.421875 ,   186742.734375 ,
         449120.125    ,   467410.25     ,   242252.140625 ,
         325181.5625   ,   223081.09375  ,   109695.5546875,   159941.5      ], 'ts_wind':[  668730.4375    ,   909338.1875    ,  1058640.875     ,
         516586.90625   ,   754774.625     ,   909874.625     ,
         372287.25      ,  1125613.25      ,   212450.59375   ,
         211878.890625  ,   611953.6875    ,    68551.4609375 ,
         768108.3125    ,   938604.9375    ,   475540.34375   ,
         341444.6875    ,  1206778.375     ,  1072823.25      ,
         209707.75      ,   161579.765625  ,   637232.6875    ,
         111058.5234375 ,   353789.75      ,   811775.375     ,
         946141.8125    ,   513450.8125    ,   383905.8125    ,
        1239141.625     ,  1106075.25      ,   274558.        ,
         157525.8125    ,   242710.109375  ,   694877.25      ,
         221302.75      ,   387798.59375   ,   835822.375     ,
         992085.4375    ,   585522.375     ,   465096.75      ,
        1306448.625     ,  1127716.375     ,   376003.46875   ,
         262230.59375   ,   309341.46875   ,   734677.625     ,
         341611.15625   ,   897978.625     ,  1027317.9375    ,
         641565.125     ,   533193.8125    ,  1371163.875     ,
        1242591.625     ,   464625.5       ,   374925.21875   ,
         404052.09375   ,   811223.6875    ,   449818.1875    ,
         949940.75      ,  1152356.75      ,   731487.6875    ,
         632564.3125    ,  1328731.375     ,  1318661.25      ,
         575718.375     ,   489012.5       ,   503957.4375    ,
         877959.625     ,   567724.        ,  1176451.625     ,
        1085111.125     ,  1239225.875     ,   811838.8125    ,
         723001.8125    ,  1228210.        ,  1317506.875     ,
        1061301.5       ,   678183.        ,   604640.75      ,
         610120.125     ,  1019876.0625    ,   679184.1875    ,
        1064924.875     ,  1183351.125     ,   957665.        ,
         869637.5625    ,  1125113.625     ,  1221260.5       ,
        1323786.875     ,   816667.5625    ,   719099.3125    ,
         722332.8125    ,   908779.125     ,  1126859.125     ,
         812075.8125    ,   926546.        ,  1267433.125     ,
        1071478.125     ,   987652.1875    ,   992131.5625    ,
        1093136.        ,  1200561.75      ,   944202.625     ,
         841807.75      ,   831524.5625    ,   766421.25      ,
         923490.5625    ,   797534.4375    ,  1268186.625     ,
        1294879.625     ,  1179975.25      ,  1100428.25      ,
         605613.3125    ,   871203.0625    ,   978584.5625    ,
        1091826.375     ,  1060980.625     ,   956020.0625    ,
         637515.875     ,  1057804.5       ,   681002.75      ,
        1170811.375     ,  1295239.375     ,  1214910.625     ,
         457551.96875   ,   766078.25      ,   881211.1875    ,
        1001023.3125    ,  1178623.        ,  1083117.625     ,
        1063405.75      ,   511700.875     ,  1177105.25      ,
         562428.6875    ,   660418.0625    ,   783159.8125    ,
        1081792.375     ,  1020829.875     ,   374478.46875   ,
        1181675.5       ,   444261.125     ,   884468.125     ,
        1015654.        ,  1147496.5       ,  1279800.        ,
        1412441.        ,   557196.4375    ,   686802.875     ,
        1046372.1875    ,   969600.625     ,   224758.90625   ,
        1270513.        ,   111162.4375    ,  1129901.25      ,
         321961.25      ,   829833.5625    ,   963491.6875    ,
        1097242.375     ,  1231062.        ,  1364937.25      ,
         450944.96875   ,   584710.375     ,   989115.9375    ,
         901584.5625    ,    60845.32421875,  1226836.625     ,
         130785.546875  ,  1098943.5       ,   207429.328125  ,
         830748.625     ,   964274.5       ,  1097925.        ,
        1231665.75      ,  1311133.125     ,   345572.96875   ,
         474638.53125   ,   605817.375     ,   953379.625     ,
         853869.9375    ,   709148.6875    ,   144821.765625  ,
        1161816.75      ,   231650.921875  ,  1030239.5625    ,
         281000.03125   ,   757300.375     ,   887036.6875    ,
        1017876.0625    ,  1149449.375     ,  1281537.875     ,
         405575.3125    ,   519712.8125    ,   641537.125     ,
         784340.375     ,   599865.75      ,   263454.5625    ,
        1193936.        ,  1058048.625     ,   938030.5       ,
         648269.0625    ,   355621.71875   ,   801379.6875    ,
         924709.125     ,  1050643.        ,  1178353.875     ,
        1298696.375     ,   448873.90625   ,   535831.75      ,
         639195.5625    ,   778615.625     ,   486159.1875    ,
        1150266.875     ,   432368.78125   ,  1012697.625     ,
         887173.875     ,   635939.25      ,   370392.96875   ,
         475697.8125    ,   802408.9375    ,   914610.6875    ,
        1042862.375     ,  1164123.875     ,  1287900.625     ,
         551048.75      ,   625359.1875    ,   713181.125     ,
         282052.        ,   738578.625     ,   468747.75      ,
        1176506.        ,  1038450.75      ,   907944.3125    ,
         594211.4375    ,   331333.875     ,   587530.1875    ,
         874383.75      ,   976254.0625    ,  1085080.5       ,
        1127779.875     ,  1165477.5       ,   739965.6875    ,
         196089.296875  ,   762503.6875    ,   446178.5625    ,
        1156598.25      ,  1043011.9375    ,   608477.6875    ,
         302244.        ,   891794.3125    ,   974806.9375    ,
         971028.9375    ,   981571.        ,  1009794.625     ,
         133451.609375  ,   114606.5859375 ,   466417.03125   ,
         818209.125     ,  1002819.125     ,  1039978.75      ,
         683042.9375    ,   329406.875     ,   887445.1875    ,
         855617.0625    ,   843954.375     ,   853292.25      ,
         882972.9375    ,  1000176.8125    ,   196278.171875  ,
          64264.375     ,    88714.125     ,   552421.75      ,
         869001.5625    ,   870218.        ,   911230.0625    ,
         429908.59375   ,   256325.21875   ,   740118.0625    ,
         718609.1875    ,   721628.5625    ,   748889.0625    ,
         978856.625     ,   310406.625     ,   196988.21875   ,
         722306.0625    ,   161488.421875  ,   599724.625     ,
         934020.25      ,   737569.25      ,   814771.6875    ,
         494064.375     ,   251381.703125  ,   336539.        ,
         656777.1875    ,   609839.375     ,   590096.75      ,
         600250.25      ,   893760.0625    ,   391393.0625    ,
         297513.59375   ,   823148.3125    ,   838475.        ,
         704558.125     ,   686599.5625    ,   948955.6875    ,
         964129.25      ,   294521.5625    ,   576432.125     ,
         645428.0625    ,  1038951.0625    ,   709157.1875    ,
         594892.125     ,   329522.5625    ,   258209.796875  ,
         246577.59375   ,   537336.3125    ,   483168.28125   ,
         462575.5625    ,   798845.6875    ,   503718.4375    ,
         418395.09375   ,   866532.3125    ,   777922.0625    ,
         670250.3125    ,   762942.75      ,   881406.8125    ,
         884783.375     ,   413056.8125    ,   413987.5       ,
         473308.65625   ,   535773.375     ,   684706.0625    ,
         301884.875     ,   191727.3125    ,   135755.625     ,
         507050.0625    ,   416187.03125   ,   353760.5       ,
         629375.8125    ,   604659.375     ,   528336.75      ,
         923294.9375    ,   236056.421875  ,   848792.3125    ,
         723014.9375    ,   432805.5       ,   588751.75      ,
         266921.25      ,   308515.5       ,   371523.1875    ,
         745499.75      ,   294442.8125    ,   161392.625     ,
          38012.9140625 ,   354666.53125   ,   442686.21875   ,
         330582.15625   ,   241744.234375  ,   473246.90625   ,
         653481.125     ,   585862.        ,   815155.4375    ,
         771210.125     ,   489359.5625    ,   579454.375     ,
         453331.5       ,   139264.03125   ,   201134.484375  ,
         298521.34375   ,   729953.8125    ,   327048.5625    ,
         199195.953125  ,    91859.6015625 ,   115152.90625   ,
         211116.015625  ,   421740.375     ,   632862.875     ,
         548792.25      ,   697630.4375    ,   659870.3125    ,
         412630.8125    ,   548571.125     ,   439476.25      ,
         543691.        ,    11564.77832031,   134444.53125   ,
         268900.28125   ,   598547.3125    ,   367146.65625   ,
         358178.9375    ,   252677.890625  ,   184504.65625   ,
         404498.71875   ,   600163.5       ,   535114.375     ,
         615562.1875    ,   543468.25      ,   426158.125     ,
         545614.5625    ,   401627.4375    ,   567999.5625    ,
         136595.25      ,   255334.890625  ,   478903.125     ,
         288917.75      ,   254081.71875   ,   285744.96875   ,
         301214.53125   ,   381815.09375   ,   484310.0625    ,
         478492.6875    ,   505826.21875   ,   425950.34375   ,
         526906.8125    ,   336393.5625    ,   360000.46875   ,
         204912.421875  ,   142902.09375   ,   186742.734375  ,
         292174.5625    ,   375563.59375   ,   433015.375     ,
         449120.125     ,   467410.25      ,   341196.125     ,
         534745.5625    ,   289708.96875   ,   242252.140625  ,
         125803.328125  ,    32823.0625    ,   242620.25      ,
         325181.5625    ,   379624.03125   ,   253196.859375  ,
         344051.40625   ,   129340.453125  ,   223081.09375   ,
         129551.390625  ,   239891.03125   ,   261754.0625    ,
         356155.5       ,   109695.5546875 ,    32649.04492188,   159941.5       ]}

        active_sites=params>0
        distances=distance_dict[self.config['data_type']]
        distances=numpy.asarray(distances)
        cost_distance=distances[active_sites == True].sum()

        cost+=cost_distance
        
        if save_result:
            self.saved['output'] = output
            self.saved['cost'] = cost
            self.saved['capacity'] = clipped * self.config['size']
                
        return cost, output
