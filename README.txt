README - simple instructions on how to run MUREIL
Marcelle Gannon marcelle.gannon@gmail.com
13 Dec 2012

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
