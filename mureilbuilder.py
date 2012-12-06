"""mureilbuilder.py collects functions that build a MUREIL simulation.

   The intended use from the top-level is to call build_master with the command-line flags,
   which will process any configuration files (identified as -f file), and any command-line
   overrides, as listed in the read_flags function.
"""

import sys
import ConfigParser
import json
import argparse
import mureilbase

def read_config_file(filename):
    """Take in a filename and parse the file sections to a nested dict object.

    Keyword arguments:
    filename -- a string for the filename to read
    
    Returns:
    config -- a nested dict containing the sections (identified by []) in the configuration file, with
    each section dict containing its parameters.

    An arbitrary collection of parameters
    and types may be entered. Parameters are parsed with the json parser, with those that are not 
    otherwise decoded recorded as strings. A list in Python syntax [1, 2, 3] etc will come through.
    """

    parsed_config = ConfigParser.RawConfigParser()
    parsed_config.read(filename)

    config = {}

    for section in parsed_config.sections():
        this_list = {}
        for item in parsed_config.items(section):
            try:
                this_list[item[0]] = json.loads(item[1])
            except ValueError:
                this_list[item[0]] = item[1]

        config[section] = this_list
    
    return config


def read_flags(flags):
    args_list = {'iterations': ('Master', 'iterations'), 
                 'seed': ('algorithm', 'seed'),
                 'pop_size': ('algorithm', 'pop_size'),
                 'optim_type': ('Master', 'optim_type'),
                 'processes': ('algorithm', 'processes'),
                 'output_file' : ('Master', 'output_file')}
    
    parser = argparse.ArgumentParser()
    
    for arg in args_list:
        parser.add_argument('--' + arg)
  
    parser.add_argument('-f', '--file', action='append')
  
    args = parser.parse_args(flags)

    dict_args = vars(args)
    
    extra_config = {}

    files = dict_args.pop('file')
    
    conf_list = []
    
    for item in dict_args.keys():
        val = dict_args[item]
        if val is not None:
            try:
                val_parsed = json.loads(val)
            except ValueError:
                val_parsed = val

            conf_tup = (args_list[item], val_parsed)
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
                print 'Parameter ' + param + ' not found'
        else:
            if section in full_config['Master']:
                sect_name = full_config['Master'][section]
                if param in full_config[sect_name]:
                    full_config[sect_name][param] = value
                else:
                    print 'Parameter ' + param + ' not found'
    
    return full_config
    

def check_param_names(default_config, new_config, identifier):
    result = True
    for param in new_config:
        if param not in default_config:
            if param not in ['class', 'module']:
                result = False
                print 'Parameter ' + param + ' not expected by ' + identifier
    
    return result


def create_instance(config):
    module_path = config['module']
    class_name = config['class']
    module = __import__(module_path)
    class_instance = getattr(module, class_name)()

    if not issubclass(class_instance.__class__, mureilbase.MureilbaseInterface):
        print class_name + ' does not implement mureilbase.MureilbaseInterface'
    
    temp_config = class_instance.get_config()
    temp_config.update(config)
    check_params = check_param_names(class_instance.get_default_config(), config, class_name + ' in ' + module_path)
    if not check_params:
        print 'Parameter check failed for ' + class_name
        
    class_instance.set_config(temp_config)
    return class_instance
    
    
def create_master_instance(full_config, flags):
    module_path = full_config['Master']['module']
    class_name = full_config['Master']['class']
    module = __import__(module_path)
    class_instance = getattr(module, class_name)()
    # Get the default master config in case the config files don't list all the Master members
    temp_config = class_instance.get_config()
    temp_config.update(full_config['Master'])
    full_config['Master'] = temp_config
    check_params = check_param_names(class_instance.get_default_config(), full_config['Master'], class_name + ' in ' + module_path)
    if not check_params:
        print 'Parameter check failed for Master'
    
    full_config = apply_flags(full_config, flags)
    class_instance.set_config(full_config)
    
    return class_instance


def build_master(raw_flags):
    files, conf_list = read_flags(sys.argv[1:])
    full_config = accum_config_files(files)
    master = create_master_instance(full_config, conf_list)
    return master
    