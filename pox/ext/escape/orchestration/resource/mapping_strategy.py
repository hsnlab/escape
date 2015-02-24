class AbstractMappingStrategy():
    """
    Abstract class for the mapping strategies

    Follow the Strategy design pattern
    """
    def __init__(self):
        pass


class ESCAPEMappingStrategy(AbstractMappingStrategy):
    """
    Implement a strategy to map initial NFFG into extNFFG
    """
    def __init__(self):
        AbstractMappingStrategy.__init__(self)