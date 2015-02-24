__author__ = 'BME-TMIT'


class AbstractMappingStrategy():
    """
    Abstract class for the mapping strategies

    Follows the Strategy design pattern
    """
    def __init__(self):
        pass


class ESCAPEMappingStrategy(AbstractMappingStrategy):
    """
    Implements a strategy to map initial NFFG into extNFFG
    """
    def __init__(self):
        AbstractMappingStrategy.__init__(self)