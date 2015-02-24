from escape.orchestration.resource.virtualization_management import AbstractVirtualizer

__author__ = 'mininet'


class ControllerAdapter():
    """
    Higher-level class for NFFG adaptation between multiple domains
    """
    def __init__(self):
        pass


class DomainVirtualizer(AbstractVirtualizer):
    """
    Specific virtualizer class for global domain virtualization

    Should be implement the same interface as AbstractVirtualizer
    """
    def __init__(self):
        AbstractVirtualizer.__init__(self)


class DomainResourceManager():
    """
    Handles and stores global resources
    """
    def __init__(self):
        pass