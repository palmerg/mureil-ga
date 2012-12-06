import abc

class MureilbaseInterface(object):
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def __init__(self):
        return
    
    @abc.abstractmethod
    def set_config(self, config):
        return
    
    @abc.abstractmethod
    def get_config(self):
        return
    
    @abc.abstractmethod
    def get_default_config(self):
        return


class Mureilbase(MureilbaseInterface):
    def __init__(self):
        self.config = self.get_default_config()
        self.is_configured = False

    def set_config(self, config):
        self.config.update(config)
        return

    def get_config(self):
        return self.config
        


