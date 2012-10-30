'''
Created on Jan 7, 2011

@author: steven
'''

#*********************************************
#Change here for different users_stuff import:----------------------- 
#*********************************************

#from users_stuff import config, gene_test, before, after
from users_stuff_rhuva import config, gene_test, before, after

#--------------------------------------------------------------------

from multiprocessing import Process, Queue
import random, sys, numpy, os, pdb, time, pickle

def multiprocess():
    """input: None
    output: None
    takes genes out of poolin and puts their position and score in poolout
    """
    while True:
        vals = poolin.get()
        if vals == 'die':
            break
        pos = vals[0]
        gene = vals[1]
        score = gene_test(gene)
        poolout.put((pos, score))
    return None

#sets up multiple Processes and Queue
global poolin
global poolout
poolin = Queue()
poolout = Queue()
for n in range(config['processes']):
    p = Process(target=multiprocess, args=())
    p.start()

def pop_score(pop):
    """input: pop class
    output: None
    sends every gene to poolin, then updates all genes scores from poolout data
    """
    n = 0
    while n < len(pop.genes):
        vals = pop.genes[n].values
        poolin.put((n, vals))
        n += 1
    for i in range(config['pop_size']):
        s = poolout.get()
        pop.genes[s[0]].score = s[1]
    return None


def clone_test(pop):
    field = []
    for base in pop.genes[0].values:
        field.append([])
    for gene in pop.genes:
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
            if total[1] >= config['pop_size']*0.9:
                matches += 1
                final.append(total[0])
    if matches == len(field):
        score = gene_test(final)
        return True, [final, score]
    else:
        return False, [[],0]

def decloner(x, results, i):
    c_bool, clone_stats = clone_test(x)
    if c_bool:
        clone_stats.append(i)
        results.append(clone_stats)
        for n in range(config['nuke_power']):
            x.mutate()
    return None

def pair_list(tall, short):
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

class Value:
    def __init__(self):
        self.value = self.rand()
        return None
    def rand(self):
        """input: None
        output: int
        returns random number between configs min & max _size
        """
        return random.randint(config['min_size'], config['max_size'])

class Gene(list):
    def __init__(self):
        self.grow()
        return None
    def grow(self):
        """input: None
        output: None
        sets up the genes score and values
        """
        self.length = random.randint(config['min_len'], config['max_len'])
        self.score = None
        self.values = []
        for i in range(self.length):
            self.base = Value()
            self.values.append(self.base.value)
        return None
    def get_score(self):
        """input: None
        output: float/int
        returns the genes score
        """
        return self.score

class Pop(list):
    def __init__(self,size=20,mort=0.5):
        """input: int(default=20), float(default=0.5)
        output: None
        sets up pop of genes and mortality rate
        """
        self.genes = []
        self.size = size
        self.mort = mort
        for i in range(size):
            self.gene = Gene()
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
            r = self.mort
            n = self.size
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
        while len(self.genes) < self.size:
            mum = random.choice(self.genes)
            dad = random.choice(self.genes)
            child = Gene()
            if len(mum.values) < len(dad.values):
                child.values = pair_list(dad.values, mum.values)
            else:
                child.values = pair_list(mum.values, dad.values)
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
                if random.random() < config['base_mute']:
                    positions.append((i,j))
            if random.random() < config['gene_mute']:
                freaks.append(i)
        for co_ord in positions:
            i = co_ord[0]
            j = co_ord[1]
            self.base = Value()
            self.genes[i].values[j] = self.base.value
        for gene_no in freaks:
            freak = self.genes[gene_no].values
            new_len = random.randint(config['min_len'], config['max_len'])
            if len(freak) >= new_len:
                freak = freak[:new_len]
            else:
                while new_len > len(freak):
                    self.base = Value()
                    freak.append(self.base.value)
            self.genes[gene_no].values = freak
        return None

def main():
    x = Pop(config['pop_size'], config['mort'])
    pop_score(x)
    before(x)
    clones_data = []
    best_gene_data = []
    for i in range(config['iteration']):
        x.mutate()
        pop_score(x)
        if i % 1 == 0:
            b_score = -1.e10
            for gene in x.genes:
                if gene.score > b_score:
                    bestgene = gene 
                    b_score = gene.score
            print b_score
        best_gene_data.append([bestgene.values[:], bestgene.score, i])
        x.lemming()
        x.breed()
        decloner(x, clones_data, i)
        print i
    pop_score(x)
    after(x, clones_data, best_gene_data)
    for n in range(config['processes']): poolin.put('die')
    pickle.dump(best_gene_data,open("GA_out.pickle","wb"))
    return None

if __name__ == '__main__':
    start = time.time()
    main()
    print 'GA calc time: %.2f seconds' % (time.time() - start)
