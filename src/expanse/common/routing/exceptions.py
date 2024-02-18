class RoutingException(Exception):
    ...


class RouteNotFound(RoutingException):
    ...


class NotEnoughURLParameters(RoutingException):
    ...
