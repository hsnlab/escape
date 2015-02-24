__author__ = 'mininet'


class AbstractAdapter():
    """
    Abstract class for different domain adapters

    Follows the Adapter design pattern
    """
    def __init__(self):
        pass


class MininetDomainAdapter(AbstractAdapter):
    """
    Adapter class to handle communication with Mininet
    """
    def __init__(self):
        AbstractAdapter.__init__(self)


class POXControllerAdapter(AbstractAdapter):
    """
    Adapter class to handle communication with POX OpenFlow controller
    """
    def __init__(self):
        AbstractAdapter.__init__(self)


class OpenStckDomainAdapter(AbstractAdapter):
    """
    Adapter class to handle communication with OpenStack
    """
    def __init__(self):
        AbstractAdapter.__init__(self)