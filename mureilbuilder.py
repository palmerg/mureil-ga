import sys
import ConfigParser
import json
import argparse

def read_config_file(filename):
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


def update_from_flags(config, flags):
    args_list = {'iterations': ('Master', 'iterations'), 
                 'seed': ('Algorithm', 'seed'),
                 'pop_size': ('Algorithm', 'pop_size'),
                 'optim_type': ('Master', 'optim_type'),
                 'processes': ('Algorithm', 'processes')}
    
    parser = argparse.ArgumentParser()
    
    for arg in args_list:
        parser.add_argument('--' + arg)
  
    args = parser.parse_args(flags)
    
    dict_args = args.__dict__
    
    extra_config = {}
    
    for item in dict_args.keys():
        val = dict_args[item]
        if val is not None:
            try:
                val_parsed = json.loads(val)
            except ValueError:
                val_parsed = val

            conf_tup = args_list[item]
            if conf_tup[0] not in extra_config:
                extra_config[conf_tup[0]] = {}
            extra_config[conf_tup[0]][conf_tup[1]] = val_parsed
        
    for section in config.items():
        if section[0] in extra_config:
            section[1].update(extra_config[section[0]])
    
    return config
        

def check_param_names(default_config, new_config):
    result = True
    for param in new_config:
        if param not in default_config:
            result = False
            print 'Parameter ' + param + ' not expected by ' + default_config['module']
    
    return result


def create_instance(config):
    module_path = config['module']
    class_name = config['class']
    module = __import__(module_path)
    class_instance = getattr(module, class_name)(config)
    return class_instance
    
def create_master_instance(config):
    module_path = config['Master']['module']
    class_name = config['Master']['class']
    module = __import__(module_path)
    class_instance = getattr(module, class_name)(config)
    return class_instance
