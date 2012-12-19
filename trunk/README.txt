README - simple instructions on how to run MUREIL
Marcelle Gannon marcelle.gannon@gmail.com
13 Dec 2012

----------
Pre-configured example
----------

At a command line outside python:

> python runmureil.py -f sample_config.txt -d INFO  

produces the following output:

CRITICAL : Run started at Thu Dec 13 14:56:19 2012
CRITICAL : Run time: 4.54 seconds
INFO     : best gene was: [138, 281, 588, 5699, 7817, 7190]
INFO     : on loop 13, with score -120923.720000
INFO     : solar: Solar_Thermal with capacities (MW): 6900.00  14050.00 
INFO     : wind: Wind with capacities (MW): 1470.00  14247.50  19542.50  17975.00 
INFO     : hydro: Basic Pumped Hydro, maximum generation capacity (MW) 2000.00
INFO     : missed_supply: Capped Missed-Supply, total 0.00 MW-timestamps missed, unreliability 0.000%
INFO     : fossil: Instant Fossil Thermal, max capacity (MW) 14362.00

See the test_ directories for more comprehensive and up to date tests.

------------
Command line
------------

Options are:
-f config-file - you can have as many of these as you like. They will accumulate the configs
	with later files taking precedence.

--iterations count - set the number of iterations to do
--seed seed - set the random seed.
--pop_size size - the size of the gene population
--processes count - how many processes to spawn in multiprocessing
--output_file filename - the name of the pickle file to write output to
--do_plots {False,True} - either False or True to print plots at the end of run

-l filename - filename for a log file. If not set, will print to screen.
-d debuglevel - one of DEBUG, INFO, WARNING, ERROR, CRITICAL. INFO is recommended.

------------
Config file format
------------

See sample_config.txt for an example. Note that each section (in square brackets) in the file is
referenced in the [Master] section so the master knows where to look. Variables in the [Global]
section are passed to all other models for their use. These may be overwritten by locally set values.

The 'simplemureilmaster.py' master does the following calculations on the global values:
- creates timestep_mins from timestep_hrs and vice-versa
- computes 'variable_cost_mult' from the length of the data set and 'time_period_yrs', if required
	values are there.

See the function 'get_config_spec' in each model's code to see the variables they expect.

-------------
Data
-------------

Use of the data/ncdatasingle.py and ncdatamulti.py models is recommended. Note that the 
SinglePassVariableGenerator model assumes the data is read in as capacity factor fractions.
