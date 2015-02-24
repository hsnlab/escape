from escape.orchestration.resource.virtualization_management import AbstractVirtualizer


class ControllerAdapter():
    """
    Higher-level class for NFFG adaptation between multiple domains
    """
    def __init__(self):
        pass


class DomainVirtualizer(AbstractVirtualizer):
    """
    Specific virtualizer class for global domain virtualization

    Should implement the same interface as AbstractVirtualizer
    """
    def __init__(self):
        AbstractVirtualizer.__init__(self)


class DomainResourceManager():
    """
    Handle and store global resources
    """
    def __init__(self):
        pass