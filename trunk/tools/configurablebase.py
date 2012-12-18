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
            mureilbuilder.update_with_globals(new_config, config_copy['global'], config_spec)
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
    