from escape.orchestration.resource.mapping_strategy import ESCAPEMappingStrategy

__author__ = 'mininet'


class AbstractMapper():
    """
    Abstract class for graph mapping function

    Contains common functions and initialization
    """
    def __init__(self):
        pass


class ResourceOrchestrationMapper(AbstractMapper):
    """
    Main class for NFFG mapping

    Uses the given mapping strategy
    """
    def __init__(self):
        AbstractMapper.__init__(self)