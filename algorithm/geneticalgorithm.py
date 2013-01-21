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
"""Module implementing genetic algorithm classes.

Created on Nov 23, 2012
by mgannon

Based on GA.py by steven, Jan 7, 2011
@author: steven
"""

import random, pickle
import tools.configurablebase as configurablebase
import tools.mureilexception as mureilexception

import logging
import sys
from itertools import groupby
from collections import defaultdict

logger = logging.getLogger(__name__)

def accumulate_capacities(json_data):
    
    json_data = sorted(json_data, key=lambda e: e['type'] + str(e['decade']))

    accumulated_values = {}

    for entry in json_data:
        key = entry['type']
        if key in accumulated_values:
            entry['capacity'] += accumulated_values[key]
        else:
            accumulated_values[key] = entry['capacity']

    return json_data
        
        


class Engine(configurablebase.ConfigurableBase):
    """Main engine for genetic algorithm. To use, call the
    following functions, in order:
    - set_config(config) where config is a dict with fields listed in
        get_config_spec
    - prepare_run() so multiprocessing can be started
    - loop through do_iteration()
    - get_final() to extract the results
    - finalise() to clean up multiprocessing
    """
    
    def __init__(self):
        configurablebase.ConfigurableBase.__init__(self)
        self.mp_active = False

    def set_config(self, config):
        """Set the configuration of the genetic algorithm, and sets
        up the starting state.
        
        Inputs: config dict - see 'get_config_spec' function for list
            of parameters.
        """
        configurablebase.ConfigurableBase.set_config(self, config)
        self.gene_test = self.config['gene_test_callback']
        
        random.seed(self.config['seed'])
        self.population = Pop(self.config)


	import json
        from os import path

        file_path = path.dirname(__file__) + '/../INITIAL.js'
	with open(file_path) as f:
            initial_data = json.load(f)
            initial_data['generators'] = accumulate_capacities(initial_data['generators'])
            
	    #filter out decades > run_year
            

	import pprint


        print [g.values for g in self.population.genes]

        # ASH CODE_CHANGE #

        # populate the gene with [solar,solar,wind,wind,wind,wind] for each runyear value (2010,2020,...2050)

        # maybe create and intermediate list with capacity by year for each technology

        # if runyear = 2010 then solar = 20 and wind = 20
        # if runyear = 2020 then solar = 20 and wind = 40
	
	self.population.genes[0].values = [1,2,3,4,5,6]
	self.population.genes[1].values = [1,2,3,4,5,6]


# perhaps here we'll insert the values from a file rather than with random values
# use seed = -999 as the indicator to do that.

        self.pop_score()
        self.clones_data = []
        self.best_gene_data = []
        self.iteration_count = -1
        self.is_configured = True
        return None


    def get_config_spec(self):
        """Return a list of tuples of format (name, conversion function, default),
        e.g. ('capex', float, 2.0). Put None if no conversion required, or if no
        default value, e.g. ('name', None, None)

        Configuration:
            processes: number of processes to spawn, if 0, no multiprocessing
            seed: integer to seed randomiser
            pop_size: integer specifying population size
            mort: float defining mortality rate
            min_len: minimum gene length
            max_len: maximum gene length
            min_param_val: minimum gene value value
            max_param_val: maximum gene value value
            base_mute: ?
            gene_mute: ?
            gene_test_callback: function handle to calculate cost of gene
        """
        return [
            ('min_param_val', int, None), 
            ('max_param_val', int, None),
            ('base_mute', float, None), 
            ('gene_mute', float, None),
            ('pop_size', int, None), 
            ('mort', float, None), 
            ('nuke_power', int, None), 
            ('runyear', int, None), 
            ('processes', int, None),
            ('seed', int, None), 
            ('min_len', int, None), 
            ('max_len', int, None),
            ('gene_test_callback', None, self.gene_test_undef)
            ]


    def gene_test_undef(self, dummy):
        raise mureilexception.ConfigException(
            'gene_test_callback not set in geneticalgorithm.py',
            __name__ + '.gene_test_undef', [])
            

    def prepare_run(self):
        """Allows for multiprocessing to be started, if
        necessary. Done here in a separate call to ensure
        the master is constructed so the finalise call will
        work, so multiprocessing does not get left running.
        """
        # Multiprocessing as implemented here does not work on Windows
        if (sys.platform == 'win32'):
            self.config['processes'] = 0
            
        if (self.config['processes'] > 0):
            # Set up the multiprocessing
            from multiprocessing import Process, Queue
            self.poolin = Queue()
            self.poolout = Queue()
            for n in range(self.config['processes']):
                p = Process(target=self.multiprocess, args=())
                p.start()
            self.mp_active = True
            logger.debug('Multiprocessing started')


    def finalise(self):
        self.end_multiprocessing()
        logger.debug('Finalising geneticalgorithm')
        return None


    def end_multiprocessing(self):
        if self.mp_active:
            for n in range(self.config['processes']):
                self.poolin.put('die')


    def multiprocess(self):
        """input: None
        output: None
        takes genes out of poolin and puts their position and score in poolout
        """
        while True:
            vals = self.poolin.get()
            if vals == 'die':
                break
            pos = vals[0]
            gene = vals[1]
            score = self.gene_test(gene)
            self.poolout.put((pos, score))
        return None


    def get_population(self):
        return self.population

        
    def get_final(self):
        self.pop_score()
        return self.population, self.clones_data, self.best_gene_data

        
    def do_iteration(self):
        if (not self.is_configured):
            msg = 'do_iteration requested, but geneticalgorithm is not configured'
            logger.critical(msg)
            raise mureilexception.ConfigException(msg, 'geneticalgorithm.do_iteration', {})

        self.iteration_count += 1
        self.population.mutate()
        self.pop_score()
        if self.iteration_count % 1 == 0:
            try:
                gene = iter(self.population.genes).next()
                b_score = gene.score
                bestgene = gene 
            except StopIteration:
                b_score = Inf
                bestgene = None

            for gene in self.population.genes:
                if gene.score > b_score:
                    bestgene = gene 
                    b_score = gene.score
            logger.debug('b_score = %f', b_score)

        self.best_gene_data.append([bestgene.values[:], bestgene.score, self.iteration_count])
        self.population.lemming()
        self.population.breed()
        self.decloner()
        logger.debug('iteration: %d', self.iteration_count)

        return None


    def pop_score(self):
        """input: pop class
        output: None
        sends every gene to poolin, then updates all genes scores from poolout data
        """
        if self.mp_active:
            for n in range(len(self.population.genes)):
                vals = self.population.genes[n].values
                self.poolin.put((n, vals))
            for n in range(len(self.population.genes)):
                # Implements a blocking get - will wait up
                # to 60 seconds for a result to be available, then
                # raise the Empty exception.
                s = self.poolout.get(True, 60)
                self.population.genes[s[0]].score = s[1]
        else:
            for n in range(len(self.population.genes)):
                vals = self.population.genes[n].values
                self.population.genes[n].score = self.gene_test(vals)


        return None


    def clone_test(self):
        field = []
        for base in self.population.genes[0].values:
            field.append([])
        for gene in self.population.genes:
            i = 0
            for base in gene.values:
                if len(field[i]) == 0:
                    field[i].append([base,1])
                else:
                    add = True
                    for tup in field[i]:
                        if tup[0] == base:
                            tup[1] += 1
                            add = False
                    if add == True:
                        field[i].append([base,1])
                i += 1
        matches = 0
        final = []
        for val_list in field:
            for total in val_list:
                if total[1] >= self.config['pop_size']*0.9:
                    matches += 1
                    final.append(total[0])
        if matches == len(field):
            score = self.gene_test(final)
            return True, [final, score]
        else:
            return False, [[],0]


    def decloner(self):
        c_bool, clone_stats = self.clone_test()
        if c_bool:
            clone_stats.append(self.iteration_count)
            self.clones_data.append(clone_stats)
            for n in range(self.config['nuke_power']):
                self.population.mutate()
        return None


class Value:
    def __init__(self, min_size, max_size):
        self.min_size = min_size
        self.max_size = max_size
        self.value = self.rand()
        return None
    def rand(self):
        """input: None
        output: int
        returns random number between configs min & max _size
        """
        return random.randint(self.min_size, self.max_size)


class Gene(list):
    def __init__(self, config):
        self.config = config
        self.grow()
        return None
    def grow(self):
        """input: None
        output: None
        sets up the genes score and values
        """
        self.length = random.randint(self.config['min_len'], self.config['max_len'])
        self.score = None
        self.values = []
        for i in range(self.length):
            self.base = Value(self.config['min_param_val'], self.config['max_param_val'])
            self.values.append(self.base.value)
        return None
    def get_score(self):
        """input: None
        output: float/int
        returns the genes score
        """
        return self.score

class Pop(list):
    def __init__(self, config):
        """input: int(default=20), float(default=0.5)
        output: None
        sets up pop of genes and mortality rate
        """
        self.genes = []
        self.config = config

        for i in range(self.config['pop_size']):
            self.gene = Gene(self.config)
            self.genes.append(self.gene)
        return None
        
    def lemming(self):
        """input: None
        output: None
        culls some genes from pop based on mortality rate and genes score
        """
        if len(self.genes) == 0:
            msg = 'geneticalgorithm found len(genes) == 0 in lemming'
            logger.critical(msg)
            raise(mureilexception.AlgorithmException(msg, {}))
            
        pop1 = self.genes
        pop2 = []
        pop3 = []
        for gene in pop1:
            pop2.append((gene.score, gene))
        pop2.sort(reverse=True)
        for tupple in pop2:
            pop3.append(tupple[1])
        self.genes = pop3
        death_note = []
        for i in range(len(self.genes)):
            r = self.config['mort']
            n = self.config['pop_size']
            prob = (r/10.5)*((float(19*n-1)/(n-1)**2)*i + 1)
            schro_cat = random.random()
            if schro_cat < prob:
                death_note.append(i)
        death_note.sort(reverse=True)
        for i in death_note:
            self.genes.pop(i)
        random.shuffle(self.genes)
        return None
    
    def breed(self):
        """input: None
        output: None
        fills pop.genes back up to original length by pairing random
        surviving genes and recombining them
        """
        if len(self.genes) == 0:
            msg = 'geneticalgorithm found len(genes) == 0 in breed'
            logger.critical(msg)
            raise(mureilexception.AlgorithmException(msg, {}))

        while len(self.genes) < self.config['pop_size']:
            mum = random.choice(self.genes)
            dad = random.choice(self.genes)
            child = Gene(self.config)
            if len(mum.values) < len(dad.values):
                child.values = self.pair_list(dad.values, mum.values)
            else:
                child.values = self.pair_list(mum.values, dad.values)
            self.genes.append(child)
        return None
    
    def mutate(self):
        """input: None
        output: None
        randomly changes some gene.value lengths and some values
        """
        positions = []
        freaks = []
        for i in range(len(self.genes)):
            for j in range(len(self.genes[i].values)):
                if random.random() < self.config['base_mute']:
                    positions.append((i,j))
            if random.random() < self.config['gene_mute']:
                freaks.append(i)
        for co_ord in positions:
            i = co_ord[0]
            j = co_ord[1]
            self.base = Value(self.config['min_param_val'], 
                self.config['max_param_val'])
            self.genes[i].values[j] = self.base.value
        for gene_no in freaks:
            freak = self.genes[gene_no].values
            new_len = random.randint(self.config['min_len'], self.config['max_len'])
            if len(freak) >= new_len:
                freak = freak[:new_len]
            else:
                while new_len > len(freak):
                    self.base = Value(self.config['min_param_val'], self.config['max_param_val'])
                    freak.append(self.base.value)
            self.genes[gene_no].values = freak
        return None
    
    def pair_list(self, tall, short):
        """input: list, list (len <= first list)
        output: list
        takes 2 parent gene.values & returns child gene.values
        """
        result = []
        if random.random() < 0.5:
            for i in range(len(tall)):
                if random.random() < 0.5 and i < len(short):
                    result.append(short[i])
                else:
                    result.append(tall[i])
        else:
            for i in range(len(short)):
                if random.random() < 0.5:
                    result.append(tall[i])
                else:
                    result.append(short[i])
        return result

