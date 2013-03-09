import pickle
import numpy
import pylab

"""Module providing helper functions for information input and
output from mureil, such as pickling.
"""

def clean_config_for_pickle(full_conf):
    """Clean out any callable method instances, such as the gene_test_callback
    parameter passed to geneticalgorithm, as these are not pickleable.
    Acts in-place on full_conf parameter.
    
    Inputs: 
        full_conf: The full_config dict structure, containing a 2-level
            configuration dict.
            
    Outputs:
        none - acts in-place on full_conf
    """
    to_del = []
    for section_key in full_conf:
        for param_key in full_conf[section_key]:
            if callable(full_conf[section_key][param_key]):
                to_del.append((section_key, param_key))
    for item in to_del:
        del full_conf[item[0]][item[1]]

    return None


def pickle_out(data, filename):
    """Write a pickle of the data object to filename.
    
    Inputs:
        data: any pickleable object
        filename: string filename
    """
    
    pickle.dump(data, open(filename, "wb"))
    ### TODO needs an exception handler on file-not-found
    return None
    
    
def pretty_print_pickle(filename):
    """Read in the pickle in filename, and pretty-print it.
    
    Inputs:
        filename: string filename, of a pickle file.
    """
    import pprint
    data = pickle.load( open( filename, "rb" ) )
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(data)
   

def compare_pickles(filename_1, filename_2):
    """Read in both pickles, and see if they match,
    and return both of them.
    
    Inputs:
        filename_1: string
        filename_2: string
        
    Outputs:
        pickle_equal: boolean - True iff the pickles have identical contents
        pickle_1: object from filename_1
        pickle_2: object from filename_2
    """
    pickle_1 = pickle.load(open(filename_1, "rb"))
    pickle_2 = pickle.load(open(filename_2, "rb"))
    pickle_equal = (pickle_1 == pickle_2)
    
    return pickle_equal, pickle_1, pickle_2


def plot_timeseries(output, demand):
    """Plot a timeseries of the output of the different generators.
    The parameter 'output' is a list of tuples of (name, timeseries).
    """
    ts = range(len(output[0][1]))
    
    pylab.figure()
    pylab.plot(ts, demand, label='demand', linewidth=2)

    cuml = numpy.zeros(len(ts), dtype=float)
    
    for pair in output:
        cuml += pair[1]
        pylab.plot(ts, cuml, label=pair[0])

    pylab.legend()        
    pylab.title('Cumulative power')

    pylab.figure()
    pylab.plot(ts, demand, label='demand', linewidth=2)

    for pair in output:
        pylab.plot(ts, pair[1], label=pair[0])

    pylab.legend()        
    pylab.title('Non-cumulative power')

    pylab.show()


def plot_pickle(filename):
    """Read in the pickle in filename, and plot the timeseries in it.
    
    Inputs:
        filename: string filename, of a pickle file.
    """
    data = pickle.load( open( filename, "rb" ) )
    output = data['best_results']['output']
    demand = data['ts_demand']
    plot_timeseries(output, demand)
       