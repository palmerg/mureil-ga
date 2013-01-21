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
import tools.mureilbuilder as mureilbuilder
import tools.mureilbase as mureilbase
import copy

class ConfigurableBase(mureilbase.ConfigurableInterface):
    def __init__(self):
        self.config = {}
        self.is_configured = False


    def set_config(self, config):
        config_spec = self.get_config_spec()
        config_copy = copy.deepcopy(config)

        # Apply defaults, then globals, then new config values
        new_config = mureilbuilder.collect_defaults(config_spec)
        if 'global' in config_copy:
            mureilbuilder.update_with_globals(new_config, config_copy['global'],
                config_spec)
            del config_copy['global']
        new_config.update(config_copy)

        # Apply conversions to config
        mureilbuilder.apply_conversions(new_config, config_spec)

        # And check that all of the required parameters are there
        mureilbuilder.check_required_params(new_config, config_spec, self.__class__.__name__)

        # And check that there aren't any extras - just check in the input config, not
        # the globals, as there may be extras there.
        mureilbuilder.check_for_extras(config_copy, config_spec, self.__class__.__name__)

        self.config = new_config
        self.is_configured = True
        return


    def get_config(self):
        return self.config

    
    def get_config_spec(self):
        return []
    