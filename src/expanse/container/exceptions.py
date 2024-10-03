class ContainerException(Exception): ...


class ResolutionException(ContainerException):
    pass


class UnboundAbstractException(ContainerException):
    pass
