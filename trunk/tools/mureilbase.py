import abc
import copy

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
    def get_config_spec(self):
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

