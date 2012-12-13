import abc

class ConfigurableInterface(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def __init__(self):
        pass
        
    @abc.abstractmethod
    def set_config(self, config):
        pass
    
    @abc.abstractmethod
    def get_config(self):
        pass
    
    @abc.abstractmethod
    def get_default_config(self):
        pass


class MasterInterface(ConfigurableInterface):

    @abc.abstractmethod
    def run(self):
        pass

    @abc.abstractmethod
    def finalise(self):
        pass
        
    @abc.abstractmethod
    def get_full_config(self):
        pass
        
    @abc.abstractmethod
    def get_default_module_configs(self, key):
        pass
        

class DataSinglePassInterface(ConfigurableInterface):

    @abc.abstractmethod
    def wind_data(self):
        pass

    @abc.abstractmethod
    def solar_data(self):
        pass

    @abc.abstractmethod
    def demand_data(self):
        pass


class ConfigurableBase(ConfigurableInterface):
    def __init__(self):
        self.config = self.get_default_config()
        self.is_configured = False

    def set_config(self, config):
        self.config.update(config)
        self.is_configured = True
        return

    def get_config(self):
        return self.config
        

class DataSinglePassBase(ConfigurableBase, DataSinglePassInterface):
    pass
    