from typing import Self

from expanse.core.http.middleware.middleware import Middleware
from expanse.core.http.middleware.middleware_group import MiddlewareGroup


class MiddlewareStack:
    def __init__(self, middlewares: list[type[Middleware]] | None = None) -> None:
        if middlewares is None:
            middlewares = self.get_default_middleware()

        self._middlewares: list[type[Middleware]] = middlewares
        self._groups: dict[str, MiddlewareGroup] = self.get_default_groups()

    @property
    def middleware(self) -> list[type[Middleware]]:
        return self._middlewares

    @property
    def groups(self) -> dict[str, MiddlewareGroup]:
        return self._groups

    def append(self, *middleware: type[Middleware]) -> Self:
        """
        Append middleware to the middleware stack.
        """
        self._middlewares.extend(middleware)

        return self

    def prepend(self, *middleware: type[Middleware]) -> Self:
        """
        Prepend middleware to the middleware stack.
        """
        self._middlewares = [*middleware, *self._middlewares]

        return self

    def use(self, middleware: list[type[Middleware]]) -> Self:
        """
        Replace the current middleware with the given middleware.
        """
        self._middlewares = middleware

        return self

    def replace(
        self, middleware: type[Middleware], replacement: type[Middleware]
    ) -> Self:
        """
        Replace a middleware with another middleware.
        """
        index = self._middlewares.index(middleware)

        self._middlewares[index] = replacement

        return self

    def remove(self, middleware: type[Middleware]) -> Self:
        """
        Remove a middleware from the stack.
        """
        self._middlewares.remove(middleware)

        return self

    def group(self, name: str) -> MiddlewareGroup:
        """
        Retrieve the middleware group with the given name.

        If does not exist it will be created automatically.
        """
        if name not in self._groups:
            self._groups[name] = MiddlewareGroup()

        return self._groups[name]

    def get_default_middleware(self) -> list[type[Middleware]]:
        from expanse.http.middleware.manage_cors import ManageCors
        from expanse.http.middleware.trust_hosts import TrustHosts
        from expanse.http.middleware.trust_proxies import TrustProxies

        return [TrustHosts, TrustProxies, ManageCors]

    def get_default_groups(self) -> dict[str, MiddlewareGroup]:
        from expanse.http.middleware.encrypt_cookies import EncryptCookies
        from expanse.session.middleware.load_session import LoadSession
        from expanse.session.middleware.validate_csrf_token import ValidateCSRFToken

        return {
            "web": MiddlewareGroup(
                [
                    EncryptCookies,
                    LoadSession,
                    ValidateCSRFToken,
                ]
            ),
            "api": MiddlewareGroup(),
        }
