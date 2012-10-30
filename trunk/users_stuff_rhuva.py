'''
Created on Jan 7, 2011

@author: steven
'''
import random, sys, os, pdb
import numpy as np
import pupynere as nc

def create_energy_config():
    energy_config = {}
    energy_config['case'] = case1
    return energy_config

def create_GA_config():
    config = {}
    config['min_size'] = 0
    config['max_size'] = 10000
    config['min_len'] = nsun_stats + nwind_stats
    config['max_len'] = nsun_stats + nwind_stats
    config['base_mute'] = 0.01
    config['gene_mute'] = 0.1
    config['pop_size'] = 100
    config['mort'] = 0.5
    config['iteration'] = 10000
    config['nuke_power'] = 20
    config['processes'] = 2
    return config


def setup_vars():
    vars = {}
    vars['solar_capex'] = 50.0                  # cost of a 50 MW solar station is $50M
    vars['wind_capex'] = 3.0                    # cost of a 2.5 MW turbine is $3M
    vars['nwind_stats'] = 20
    vars['nsun_stats'] = 10
    vars['hydro_capex'] = 2.0                   # $2B per GW cap
    vars['gas_capex'] = 1.0                     # $1B per GW cap
    vars['gas_price'] = 60                      # $ per MWh
    vars['carbon_tax'] = 20
    vars['hydro_gen'] = 2000                    # max power  (MW)
    vars['hydro_cap'] = 10000                   # max water
    vars['hydro_res'] = 5000                    # current units of water
    vars['hydro_res_temp'] = vars['hydro_cap']
    vars['water_factor'] = 0.01                 # units of water per GWh
    vars['solar_size'] = 50                  # MW
    vars['wind_turbine'] = 2.5                  # MW
    vars['nturbs'] = 40                         # initial guess
    vars['nsun_plants'] = 10                    # initial guess
    vars['nsteps'] = 1464
    return vars

def params_setup(nwind_stats,nsun_stats,nturbs,nsun_plants):
    params=np.zeros(nwind_stats+nsun_stats)
    params[:nsun_stats]=nsun_plants
    params[nsun_stats:nwind_stats+nsun_stats]=nturbs
    return params

def elec_calc(nsteps,nwind_stats,nsun_stats,ts_wind,params,ts_solar,solar_size):   
    icount=0
    elec=np.zeros(nsteps)
    elec_solar=np.zeros(nsteps)
    elec_wind=np.zeros(nsteps)
    
    for i in range(nsun_stats):
        elec_solar += ts_solar[:,i] * params[icount] * solar_size #ts_solar should already be in units of capacity
        icount += 1
    for i in range(nwind_stats):
        elec_wind += ts_wind[:,i] * params[icount] / 1000.0
        icount += 1

    elec = elec_wind + elec_solar

    return elec

def calc_cost(gene,ts_demand,elec,optim_type,wind_capex,solar_capex,nsun_stats,nwind_stats,hydro_cap,hydro_res,hydro_res_temp,hydro_gen,hydro_capex,water_factor,carbon_tax,gas_price,gas_capex):

    params=np.array(gene)
    
    if optim_type == 'match_demand':
        cost = abs(ts_demand-elec).sum()/1000.0  #now in GW
    if optim_type == 'missed_supply':
        
        cost_solar = params[0:nsun_stats].sum()*solar_capex
        cost_wind = params[nsun_stats:nsun_stats+nwind_stats].sum()*wind_capex
        
        hydro = hydro_elec(elec,ts_demand,hydro_cap,hydro_res,hydro_res_temp,hydro_gen,hydro_capex,water_factor)
        hydro_cost=hydro[0]
        elec = hydro[1]
        
        gas = gas_elec(elec,ts_demand,carbon_tax,gas_price,gas_capex)
        gas_cost = gas[0]
        elec = gas[1]
        
        ineg = (ts_demand - elec) > 0
        if ineg.any():
            cost_failedsupply = float((ts_demand[ineg] - elec[ineg]).sum())/200
        else:
            cost_failedsupply = 0.0

        cost = cost_failedsupply + cost_wind + cost_solar + hydro_cost + gas_cost
    #pdb.set_trace()
    return cost


def hydro_elec(elec,ts_demand,hydro_cap,hydro_res,hydro_res_temp,hydro_gen,hydro_capex,water_factor):
    
    hydro_res_temp = hydro_res
    extra_power = np.zeros(len(elec))
    
    for i in range(len(elec)):
        
        if ts_demand[i] > elec[i]:
            elec_diff = ts_demand[i] - elec[i]
            if elec_diff > hydro_gen:
                elec_diff = hydro_gen
            water = elec_diff * water_factor
            if water > hydro_res_temp:
                water = hydro_res_temp
            hydro_res_temp = hydro_res_temp - water
            extra_power[i] = water / water_factor
            elec[i] = elec[i] + extra_power[i]

        if elec[i] > ts_demand[i]:
            elec_diff = elec[i] - ts_demand[i]
            if elec_diff > hydro_gen:
                elec_diff = hydro_gen
            water = elec_diff * water_factor * 0.8
            if water > hydro_cap - hydro_res_temp:
                water = hydro_cap - hydro_res_temp
            hydro_res_temp = hydro_res_temp + water
            extra_power[i] = water / water_factor
            elec[i] = elec[i] - extra_power[i]

    hydro_max = extra_power.max()
    hydro_cost = hydro_max * hydro_capex    
    
    return hydro_cost,elec

def gas_elec(elec,ts_demand,carbon_tax,gas_price,gas_capex):

    diff = ts_demand - elec
    ii = (diff > 0)
    if ii.any():
        gas_cap = diff[ii].max() / 1000.0
        gas_cost_I = diff[ii].sum() / 2.0 * (gas_price + carbon_tax)/1000.0
        elec[ii] = ts_demand[ii]
    else:
        gas_cost_I = 0
        gas_cap = 0
    
    gas_cost = gas_cost_I + gas_cap * gas_capex * 1000.0
    
    return gas_cost,elec

def case0(vars):
    dir='./'
    file='CoV_output.nc'
    infile=dir+file
    f=nc.NetCDFFile(infile)
    vars['ts_wind']=f.variables['ts_wind'][:,:]
    vars['ts_solar']=f.variables['ts_solar'][:,:]
    vars['ts_demand']=f.variables['ts_demand'][:]
    vars['optim_type'] = 'missed_supply' # this means there is no cap_ex cost for infrastructure
    vars['hydro'] = 0
    vars['gas'] = 0
    return None
def case1(vars):
    dir='./access_2month_optim/'
    file='CoV_wind_station_output_II.nc' #file with _II has smaller exclusion zone
    infile=dir+file
    f=nc.NetCDFFile(infile)
    vars['ts_wind']=f.variables['CoV_wind'][:,:]

    file='CoV_dsr_station_output.nc'
    infile=dir+file
    f=nc.NetCDFFile(infile)
    vars['ts_solar']=f.variables['CoV_dsr'][:,:]

    file='Aus_demand_sample.nc'
    infile=dir+file
    f=nc.NetCDFFile(infile)
    vars['ts_demand']=f.variables['ts_demand'][:]
    vars['optim_type']='missed_supply'
    vars['hydro'] = 0
    vars['gas'] = 0
    return None
    
#Room for more cases here.

energy_config = create_energy_config()

vars = setup_vars()
energy_config['case'](vars)
for key in vars:
    locals()[key] = vars[key]

config = create_GA_config()

def gene_test(values):
    """input: list
    output: float
    takes the gene.values, tests it and returns the genes score
    """
    elec = elec_calc(nsteps,nwind_stats,nsun_stats,ts_wind,values,ts_solar,solar_size)

    score = -1 * calc_cost(values,ts_demand,elec,optim_type,wind_capex,solar_capex,nsun_stats,nwind_stats,hydro_cap,hydro_res,hydro_res_temp,hydro_gen,hydro_capex,water_factor,carbon_tax,gas_price,gas_capex)

    return score

def before(pop):
    """input: None
    output: None
    prints values, scores, ect. at beginning
    """
    num = 0
    sum = 0
    for gene in pop.genes:
        num += 1
        sum += gene.score
    print 'average score before:', float(sum)/num
    return None

def after(pop, clones_data, best_gene_data):
    """input: None
    output: None
    prints values, scores, ect. at end
    """
    num = 0
    sum = 0
    for gene in pop.genes:
        num += 1
        sum += gene.score
    optim = [[],-1e1000,-1]
    for data in best_gene_data:
        if data[1] > optim[1]:
            optim = data
    print 'best gene was: %s' % str(optim[0])
    print 'on loop %i, with score %f' % (optim[2], optim[1])
    for data in clones_data:
        if data[1] > optim[1]:
            optim = data
    print '%i nuke/s dropped' % len(clones_data)
    print 'average score after:', float(sum)/num   
    return None

def data_print(pop):
    """
    print the best genes
    from the final iteration
    and their score
    """

    icount=0
    score_count=[]
    for gene in pop.genes:
        score_count.append(gene.score)
    score_count=np.asarray(score_count)
    print '\nThe best gene(s) and score:\n'
    for gene in pop.genes:
        if score_count[icount] == score_count.max():
            print gene.values, gene.score
        icount+=1
    return None
