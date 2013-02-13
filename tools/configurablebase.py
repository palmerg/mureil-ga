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

from tools import mureilbuilder, mureilbase

import copy

class ConfigurableBase(mureilbase.ConfigurableInterface):
    def __init__(self):
        """Initialise self.config to empty and self.config_spec to 
        self.get_config_spec.
        """
        self.config = {}
        self.config_spec = self.get_config_spec()
        self.is_configured = False


    def set_config(self, config, global_config=None):
        """Set the config to the values in config, with those in global_config
        also applied, using self.config_spec to apply defaults, convert parameters
        and check that all are present and none are extras.
        
        Calls, in turn:
            load_initial_config (loads defaults, then applies config and global, check all required present)
            process_initial_config (empty here - may determine extra parameters required and update the config_spec)
            update_config_from_spec (process an updated config_spec)
            check_config (check all parameters for existence, and that there are no extras)
            complete_configuration (empty, for classes that do further processing)
        """
        
        self.load_initial_config(config, global_config)
        self.process_initial_config()
        self.update_from_config_spec()
        self.check_config()
        self.complete_configuration()
        

    def update_config(self, new_config):
        """Update the current config values with new_config, for all parameters
        in new_config.
        """
        self.config.update(new_config)


    def load_initial_config(self, config, global_config=None):
        config_spec = self.config_spec
        config_copy = copy.deepcopy(config)
        
        # Apply defaults, then globals, then new config values

        # Defaults
        new_config = mureilbuilder.collect_defaults(config_spec)
        
        # Globals
        if global_config:
            mureilbuilder.update_with_globals(new_config, global_config,
                config_spec)

        # New config values
        new_config.update(config_copy)

        # Apply conversions to config
        mureilbuilder.apply_conversions(new_config, config_spec)

        # And check that all of the required parameters are there
        mureilbuilder.check_required_params(new_config, config_spec)

        self.config = new_config
        return


    def process_initial_config(self):
        return
        
        
    def update_from_config_spec(self):
        """Reapply the config_spec, which may have been changed in process_initial_config.
        
        Applies any new defaults and applies conversions.
        """

        # Get defaults
        new_config = mureilbuilder.collect_defaults(self.config_spec)
        
        # Copy defaults to params that are not in self.config already
        for (key, value) in new_config.iteritems():
            if key not in self.config:
                self.config[key] = value
        
        # Apply conversions to config
        mureilbuilder.apply_conversions(self.config, self.config_spec)


    def check_config(self):
        """Final check that all requested parameters are present, and that there are no
        extras.
        """
        
        # And check that all of the required parameters are there
        mureilbuilder.check_required_params(self.config, self.config_spec)

        # And check that there aren't any extras
        mureilbuilder.check_for_extras(self.config, self.config_spec)


    def complete_configuration(self):
        self.is_configured = True


    def get_config(self):
        return self.config

    
    def get_config_spec(self):
        return []
    