__author__ = 'mininet'


class AbstractVirtualizer():
    """
    Abstract class for actual virtualizers

    Follows the Proxy design pattern
    """
    def __init__(self):
        pass


class PolicyEnforcement(AbstractVirtualizer):
    """
    Proxy class for policy checking
    """
    def __init__(self):
        AbstractVirtualizer.__init__(self)


class ESCAPEVirtualizer(AbstractVirtualizer):
    """
    Actual virtualizer class for ESCAPE
    """
    def __init__(self):
        AbstractVirtualizer.__init__(self)


class VirtualizerManager():
    """
    Stores, handles and organizes Virtualizer instances
    """
    def __init__(self):
        pass