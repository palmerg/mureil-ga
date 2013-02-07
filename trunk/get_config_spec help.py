""" Prints the docstring of the get_config_spec method from all python modules
    within the tree beneath the directory os.getcwd(). Prints to both stdout
    and to a file get_config_spec.txt
    EH, 14.01.2013
    
"""

import os
import inspect
import string
from generator import singlepassgenerator


def list_modules(directory):
    mod_list = []
    for dirpath, dirnames, filenames in os.walk(directory):
           path_list = string.split(dirpath, "\\")
           mod_pkg = string.join(path_list[2:], ".")

           for file_name in filenames:
                  full_path = os.path.join(dirpath, file_name)
                  name, ext = os.path.splitext(full_path)
                  if ext == ".py":
                      x = len(file_name)-len(".py")
                      just_name = file_name[0:x]
                      if len(mod_pkg) > 0:
                          mod_full = mod_pkg + "." + just_name
                      else:
                          mod_full = just_name           

                      mod_list.append(mod_full)

    #print mod_list
    return mod_list


def my_import(name):
    """ Returns the module object from the string 'name'
    """   
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def print_docstring(module_list):
    """ Prints the docstring of the get_config_spec method from the modules
        within the list file_list"""
    out_file = os.path.join (cur_dir, "get_config_spec help.txt");
    f = open(out_file, "w")
    for module_name in module_list:
        if string.find(module_name, ".")< 0:
            module = module_name
        else:
            module = my_import(module_name)       
        for name, obj in inspect.getmembers(module):          
                if inspect.isclass(obj):
                    if issubclass(obj, singlepassgenerator.SinglePassGeneratorBase):
                        print "------------------------------------------------------------------------------"
                        print "Module: " + module_name
                        print "Class:  " + name
                        print "------------------------------------------------------------------------------"
                        print obj.get_config_spec.__doc__

                        f.write("------------------------------------------------------------------------------" + "\n") 
                        f.write("Module: " + module_name + "\n")
                        f.write("Class:  " + name + "\n")
                        f.write("------------------------------------------------------------------------------" + "\n")
                        help_doc = str(obj.get_config_spec.__doc__)
                        f.write(help_doc + "\n")

    f.close


if __name__ == '__main__':    
    cur_dir = os.getcwd()
    mod_list= list_modules(cur_dir)
    print_docstring(mod_list)

