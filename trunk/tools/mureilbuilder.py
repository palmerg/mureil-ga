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
"""mureilbuilder.py collects functions that build a MUREIL simulation.

   The intended use from the top-level is to call build_master with the command-line flags,
   which will process any configuration files (identified as -f file), and any command-line
   overrides, as listed in the read_flags function.
"""

import sys, os
import ConfigParser
import argparse
import tools.mureilbase as mureilbase
import importlib
import logging
import tools.mureilexception as mureilexception
import string
import copy

logger = logging.getLogger(__name__)

def read_config_file(filename):
    """Take in a filename and parse the file sections to a nested dict object.

    Keyword arguments:
    filename -- a string for the filename to read
    
    Returns:
    config -- a nested dict containing the sections (identified by []) in the configuration file, with
    each section dict containing its parameters.
    """

    parsed_config = ConfigParser.RawConfigParser()
    read_file = parsed_config.read(filename)

    # ConfigParser.read_file returns a list of filenames read
    if read_file == []:
        msg = 'Configuration file ' + filename + ' not opened.'
        logger.critical(msg)
        raise mureilexception.ConfigException(msg, __name__, {})

    config = {}

    for section in parsed_config.sections():
        this_list = {}
        for item in parsed_config.items(section):
            this_list[item[0]] = item[1]

        config[section] = this_list
    
    return config


def read_flags(flags):
    args_list = {'iterations': ('Master', 'iterations'), 
                 'seed': ('algorithm', 'seed'),
                 'pop_size': ('algorithm', 'pop_size'),
                 'optim_type': ('Master', 'optim_type'),
                 'processes': ('algorithm', 'processes'),
                 'output_file' : ('Master', 'output_file'),
                 'do_plots' : ('Master', 'do_plots')}
                 
    parser = argparse.ArgumentParser()
    
    for arg in args_list:
        parser.add_argument('--' + arg)
  
    parser.add_argument('-f', '--file', action='append')
  
    parser.add_argument('-l', '--logfile')
    parser.add_argument('-d', '--debuglevel')
    parser.add_argument('--logmodulenames', action='store_true', default=False)
  
    args = parser.parse_args(flags)

    dict_args = vars(args)
    
    logger_config = {}
    for arg in ['logfile', 'debuglevel', 'logmodulenames']:
        logger_config[arg] = dict_args.pop(arg)

    do_logger_setup(logger_config)

    files = dict_args.pop('file')
    
    conf_list = []
    
    for item in dict_args.keys():
        val = dict_args[item]
        if val is not None:
            conf_tup = (args_list[item], val)
            conf_list.append(conf_tup)
    
    return files, conf_list


def accum_config_files(files):
    config = {}
    for conf_file in files:
        next_conf = read_config_file(conf_file)
        for section in next_conf.items():
            if section[0] in config:
                config[section[0]].update(section[1])
            else:
                config[section[0]] = section[1]

    return config
    

def apply_flags(full_config, flags):
    for flag in flags:
        pair, value = flag
        section, param = pair
        
        if (section == 'Master'):
            if param in full_config['Master']:
                full_config['Master'][param] = value
            else:
                msg = ('Flag ' + flag + ' alters parameter ' + param + 
                    ' in Master, but this parameter does not exist') 
                logging.error(msg)
                raise mureilexception.ConfigException(msg, __name__ + '.apply_flags', {})
        else:
            if section in full_config['Master']:
                sect_name = full_config['Master'][section]
                if param in full_config[sect_name]:
                    full_config[sect_name][param] = value
                else:
                    msg = 'Flag ' + str(flag) + ' alters parameter ' + str(param) + ' in ' + str(section) + ', but this parameter does not exist' 
                    logging.error(msg)
                    raise mureilexception.ConfigException(msg, __name__ + '.apply_flags', {})

    
def check_subclass(class_instance, subclass, caller):
    if not issubclass(class_instance.__class__, subclass):
        msg = 'in ' + caller + ' ' + class_instance.__class__.__name__ + ' does not implement ' + subclass.__name__
        logging.critical(msg)
        raise(mureilexception.ClassTypeException(msg, caller, 
            class_instance.__class__.__name__, subclass.__name__, {}))


def create_instance(config, section_name, subclass):
    model_name = config['model']
    parts = model_name.split('.')
    module_name = string.join(parts[0:-1], '.')
    class_name = parts[-1]

    try:
        module = importlib.import_module(module_name)
        class_instance = getattr(module, class_name)()
    except TypeError as me:
        msg = 'Object (' + module_name + ', ' + class_name + '), requested in section ' + section_name + ' does not fully implement its subclasses'
        logger.critical(msg, exc_info=me)
        raise mureilexception.ConfigException(msg, __name__, {})
    except (ImportError, AttributeError, NameError) as me:
        msg = 'Object (' + module_name + ', ' + class_name + '), requested in section ' + section_name + ' could not be loaded.'
        logger.critical(msg, exc_info=me)
        raise mureilexception.ConfigException(msg, __name__, {})

    check_subclass(class_instance, subclass, __name__ + '.create_instance')

    config['section'] = section_name
    class_instance.set_config(config)
    return class_instance
    
    
def create_master_instance(full_config, flags, extra_data):
    model_name = full_config['Master']['model']
    parts = model_name.split('.')
    module_name = string.join(parts[0:-1], '.')
    class_name = parts[-1]
    
    try:
        module = importlib.import_module(module_name)
        class_instance = getattr(module, class_name)()
    except TypeError as me:
        msg = 'Requested Master of module: ' + module_name + ', class: ' + class_name + ' does not fully implement its subclasses'
        logger.critical(msg, exc_info=me)
        raise mureilexception.ConfigException(msg, __name__, {})
    except (ImportError, AttributeError, NameError) as me:
        msg = 'Requested Master of module: ' + module_name + ', class: ' + class_name + ' could not be loaded.'
        logger.critical(msg, exc_info=me)
        raise mureilexception.ConfigException(msg, __name__, {})
        
    check_subclass(class_instance, mureilbase.MasterInterface, __name__ + '.create_master_instance')

    full_config['flags'] = flags
    full_config['extra_data'] = extra_data
    class_instance.set_config(full_config)
    
    return class_instance


def build_master(raw_flags, extra_data = None):
    files, conf_list = read_flags(raw_flags)
    full_config = accum_config_files(files)
    master = create_master_instance(full_config, conf_list, extra_data)
            
    return master



def collect_defaults(config_spec):
    new_config = {}
    for config_tup in filter(lambda t: t[2] is not None, config_spec):
        new_config[config_tup[0]] = config_tup[2]
    return new_config
    

def apply_conversions(config, config_spec):
    # Apply conversions, in second position in tuple
    for config_tup in filter(lambda t: t[1] is not None, config_spec):
        if config_tup[0] in config:
            old_val = config[config_tup[0]]
            config[config_tup[0]] = config_tup[1](old_val)


def check_required_params(config, config_spec, class_name):
    for config_tup in config_spec:
        if config_tup[0] not in config:
            if config_tup[0] not in ['model', 'section']:
                msg = (class_name + ' requires parameter ' + config_tup[0] + 
                    ' but it is not provided in section ' + config['section'])
                logging.critical(msg)
                raise mureilexception.ConfigException(msg, __name__ + '.check_required_params', {})


def check_for_extras(config, config_spec, class_name):
    for config_item in config:
        if config_item not in ['model', 'section']:
            if filter(lambda t: t[0] == config_item, config_spec) == []:
                logging.warning(class_name + ' not expecting parameter ' + config_item +
                    ' in section ' + config['section'])


def check_all_globals_present(config, required, class_name):
    for param in required:
        if param not in config:
            msg = (class_name + ' requires parameter ' + param + ' in global section')
            logging.critical(msg)
            raise mureilexception.ConfigException(msg, __name__ + '.check_all_globals_present', {})


def check_section_exists(full_config, src, section):
    if section not in full_config:
        msg = ('Section ' + section + ' required in config, as specified in Master')
        logger.critical(msg)
        raise mureilexception.ConfigException(msg, src, {})

            

def make_string_list(val):
    """Check if the item is a string, and if so, apply str.split() to make a list of
    strings. If it's a list of strings, return as is. This allows configuration parameters
    such as dispatch_order to be initialised from a string or from a config pickle.
    """
    if isinstance(val, str):
        return str.split(val)
    else:
        return val


def make_int_list(val):
    """Check if the item is a string, and if so, apply str.split() to make a list of
    ints. If it's a list of ints, return as is. This allows configuration parameters
    such as dispatch_order to be initialised from a string or from a config pickle.
    """
    if isinstance(val, str):
        return map(int, str.split(val))
    else:
        return val


def string_to_bool(val):
    """Convert 'False' to False and 'True' to True and everything else to 'False'
    """
    return (val == 'True')
        

def update_with_globals(new_config, global_conf, config_spec):
    for tup in config_spec:
        if tup[0] in global_conf:
            new_config[tup[0]] = global_conf[tup[0]]


def do_logger_setup(logger_config):

    for arg in ['debuglevel', 'logmodulenames', 'logfile']:
        if arg not in logger_config:
            logger_config[arg] = None

    # First, remove any existing handlers
    root = logging.getLogger()
    if root.handlers:
        handlers = copy.copy(root.handlers)
        for handler in handlers:
            root.removeHandler(handler)
 
    if logger_config['debuglevel'] is None:
        debuglevel = 'INFO'
    else:
        debuglevel = logger_config['debuglevel']

    numeric_level = getattr(logging, debuglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid debug level: %s' % debuglevel)

    # Now create the new handler

    if logger_config['logmodulenames']:
        format_string = '%(levelname)-8s : %(name)s : %(message)s'
    else:
        format_string = '%(levelname)-8s : %(message)s'

    formatter = logging.Formatter(format_string)

    if logger_config['logfile'] is not None:
        handler = logging.FileHandler(logger_config['logfile'], mode='w')
    else:
        handler = logging.StreamHandler()
 
    handler.setFormatter(formatter)
    root.addHandler(handler) 
    root.setLevel(numeric_level)
 
 
def unittest_path_setup(self, thisfile):
    test_dir = os.path.dirname(os.path.realpath(thisfile)) 
    self.cwd = os.getcwd()
    os.chdir(test_dir)
    do_logger_setup({})
