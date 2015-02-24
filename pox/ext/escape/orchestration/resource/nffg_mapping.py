from escape.orchestration.resource.mapping_strategy import ESCAPEMappingStrategy


class AbstractMapper():
    """
    Abstract class for graph mapping function

    Contain common functions and initialization
    """
    def __init__(self):
        pass


class ResourceOrchestrationMapper(AbstractMapper):
    """
    Main class for NFFG mapping

    Use the given mapping strategy
    """
    def __init__(self):
        AbstractMapper.__init__(self)