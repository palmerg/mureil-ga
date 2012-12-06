'''
Created on Nov 23, 2012
by mgannon

Based on GA.py by steven, Jan 7, 2011
@author: steven
'''

import random, pickle
import mureilbase

class Engine(mureilbase.Mureilbase):
    def set_config(self, config):
        """input: config, dict containing:
        processes: number of processes to spawn, if 0, no multiprocessing
        seed: integer to seed randomiser
        pop_size: integer specifying population size
        mort: float defining mortality rate
        min_len: minimum gene length
        max_len: maximum gene length
        min_size: minimum gene value value
        max_size: maximum gene value value
        base_mute: ?
        gene_mute: ?
        gene_test_callback: function handle to calculate cost of gene
        output: None
        Sets up engine to run genetic algorithm
        """
        self.config.update(config)
        self.gene_test = config['gene_test_callback']
        random.seed(config['seed'])
        self.population = Pop(self.config)
        if (self.config['processes'] > 0):
            # Set up the multiprocessing
            from multiprocessing import Process, Queue
            self.poolin = Queue()
            self.poolout = Queue()
            for n in range(self.config['processes']):
                p = Process(target=self.multiprocess, args=())
                p.start()
        self.pop_score()
        self.clones_data = []
        self.best_gene_data = []
        self.iteration_count = -1
        self.is_configured = True
        return None


    def get_default_config(self):
        config = {
            'module': 'geneticalgorithm',
            'class': 'Engine',
            'min_size': 0,
            'max_size': 10000,
            'base_mute': 0.01,
            'gene_mute': 0.1,
            'pop_size': 50,
            'mort': 0.5,
            'nuke_power': 20,
            'processes': 0,
            'seed': 12345,
            'min_len': 10,
            'max_len': 10,
            'gene_test_callback': None
        }
        
        return config
    

    def tidy_up(self):
        if (self.config['processes'] > 0):
            for n in range(self.config['processes']):
                self.poolin.put('die')
        return None

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
        self.iteration_count += 1
        self.population.mutate()
        self.pop_score()
        if self.iteration_count % 1 == 0:
            b_score = -1.e10
            for gene in self.population.genes:
                if gene.score > b_score:
                    bestgene = gene 
                    b_score = gene.score
            print b_score
        self.best_gene_data.append([bestgene.values[:], bestgene.score, self.iteration_count])
        self.population.lemming()
        self.population.breed()
        self.decloner()
        print self.iteration_count
        return None

    def pop_score(self):
        """input: pop class
        output: None
        sends every gene to poolin, then updates all genes scores from poolout data
        """
        if (self.config['processes'] == 0):
            for n in range(len(self.population.genes)):
                vals = self.population.genes[n].values
                self.population.genes[n].score = self.gene_test(vals)
        else:
            for n in range(len(self.population.genes)):
                vals = self.population.genes[n].values
                self.poolin.put((n, vals))
            for n in range(len(self.population.genes)):
                s = self.poolout.get()
                self.population.genes[s[0]].score = s[1]

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
            self.base = Value(self.config['min_size'], self.config['max_size'])
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
            print 'score one for the Grim Reaper'
            sys.exit()
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
            print 'score one for the Grim Reaper'
            sys.exit()
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
            self.base = Value(self.config['min_size'], 
                self.config['max_size'])
            self.genes[i].values[j] = self.base.value
        for gene_no in freaks:
            freak = self.genes[gene_no].values
            new_len = random.randint(self.config['min_len'], self.config['max_len'])
            if len(freak) >= new_len:
                freak = freak[:new_len]
            else:
                while new_len > len(freak):
                    self.base = Value(self.config['min_size'], self.config['max_size'])
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

