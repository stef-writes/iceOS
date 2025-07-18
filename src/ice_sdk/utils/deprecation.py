import logging

logger = logging.getLogger(__name__)

def deprecated(version: str, replacement: str):
    def wrapper(cls):
        def warn():
            logger.warning(f"{cls.__name__} deprecated in {version}. Use {replacement} instead")
        
        # Show warning on class instantiation
        orig_init = cls.__init__
        def new_init(self, *args, **kwargs):
            warn()
            orig_init(self, *args, **kwargs)
        
        cls.__init__ = new_init
        return cls
    return wrapper