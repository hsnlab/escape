from escape.orchestration.resource.mapping_strategy import AbstractMappingStrategy
from escape.orchestration.resource.nffg_mapping import AbstractMapper

__author__ = 'mininet'


class ServiceGraphMapper(AbstractMapper):
    """
    Helper class for mapping Service Graph to NFFG
    """
    def __init__(self):
        AbstractMapper.__init__(self)


class DefaultServiceMappingStrategy(AbstractMappingStrategy):
    """
    Mapping class which maps given Service Graph into a single BiS-BiS
    """
    def __init__(self):
        AbstractMappingStrategy.__init__(self)