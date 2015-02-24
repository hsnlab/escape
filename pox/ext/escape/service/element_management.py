class AbstractElementManager():
    """
    Abstract class for element management components (EM)
    """
    def __init__(self):
        pass


class ClickManager(AbstractElementManager):
    """
    Manager class for specific VNF management based on Clicky
    """
    def __init__(self):
        AbstractElementManager.__init__(self)