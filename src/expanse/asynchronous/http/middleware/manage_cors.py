import re

from expanse.asynchronous.container.container import Container
from expanse.asynchronous.core.http.middleware.middleware import Middleware
from expanse.asynchronous.http.request import Request
from expanse.asynchronous.http.response import Response
from expanse.asynchronous.types.http.middleware import RequestHandler
from expanse.common.configuration.config import Config


class Cors:
    def __init__(
        self,
        allowed_origins: list[str] | None = None,
        allowed_origins_patterns: list[str] | None = None,
        allowed_methods: list[str] | None = None,
        allowed_headers: list[str] | None = None,
        exposed_headers: list[str] | None = None,
        supports_credentials: bool = False,
        max_age: int | None = 0,
    ) -> None:
        self._allowed_origins: list[str] = allowed_origins or []
        self._allowed_origins_patterns: list[str] = allowed_origins_patterns or []
        self._allowed_methods: list[str] = allowed_methods or []
        self._allowed_headers: list[str] = allowed_headers or []
        self._exposed_headers: list[str] = exposed_headers or []
        self._supports_credentials: bool = supports_credentials
        self._max_age: int | None = max_age

        self._allow_all_origins: bool = False
        self._allow_all_headers: bool = False
        self._allow_all_methods: bool = False

        self._normalize()

    def set_options(
        self,
        allowed_origins: list[str] | None = None,
        allowed_origins_patterns: list[str] | None = None,
        allowed_methods: list[str] | None = None,
        allowed_headers: list[str] | None = None,
        exposed_headers: list[str] | None = None,
        supports_credentials: bool = False,
        max_age: int | None = 0,
        **kwargs,
    ) -> None:
        self._allowed_origins = allowed_origins or []
        self._allowed_origins_patterns = allowed_origins_patterns or []
        self._allowed_methods = allowed_methods or []
        self._allowed_headers = allowed_headers or []
        self._exposed_headers = exposed_headers or []
        self._supports_credentials = supports_credentials
        self._max_age = max_age

        self._normalize()

    def is_cors_request(self, request: Request) -> bool:
        return "Origin" in request.headers

    def is_preflight_request(self, request: Request) -> bool:
        return (
            request.method == "OPTIONS"
            and "Access-Control-Request-Method" in request.headers
        )

    def handle_preflight_request(self, request: Request) -> Response:
        response = Response(status_code=204)

        return self.add_preflight_request_headers(response, request)

    def add_preflight_request_headers(
        self, response: Response, request: Request
    ) -> Response:
        self._configure_allowed_origins(response, request)

        if "Access-Control-Allow-Origin" in response.headers:
            self._configure_allow_credentials(response, request)

            self._configure_allowed_methods(response, request)

            self._configure_allowed_headers(response, request)

            self._configure_max_age(response, request)

        return response

    def add_actual_request_headers(
        self, response: Response, request: Request
    ) -> Response:
        self._configure_allowed_origins(response, request)

        if "Access-Control-Allow-Origin" in response.headers:
            self._configure_allow_credentials(response, request)

            self._configure_exposed_headers(response, request)

        return response

    def is_origin_allowed(self, request: Request) -> bool:
        if self._allow_all_origins:
            return True

        origin = request.headers.get("Origin", "")

        if origin in self._allowed_origins:
            return True

        for pattern in self._allowed_origins_patterns:
            if re.match(pattern, origin):
                return True

        return False

    def vary_header(self, response: Response, header: str) -> Response:
        if "Vary" not in response.headers:
            response.headers["Vary"] = header
        elif header not in response.headers["Vary"].split(", "):
            response.headers["Vary"] += f", {header}"

        return response

    def _normalize(self) -> None:
        # We normalize case first
        self._allowed_headers = [header.lower() for header in self._allowed_headers]
        self._allowed_methods = [method.lower() for method in self._allowed_methods]

        # Normalize ["*"] to true
        self._allow_all_origins = "*" in self._allowed_origins
        self._allow_all_headers = "*" in self._allowed_headers
        self._allow_all_methods = "*" in self._allowed_methods

        if not self._allow_all_origins:
            for origin in self._allowed_origins:
                if "*" in origin:
                    self._allowed_origins_patterns.append(
                        self._convert_wildcard_to_pattern(origin)
                    )

    def _convert_wildcard_to_pattern(self, pattern: str) -> str:
        pattern = re.escape(pattern)
        pattern = pattern.replace(r"\*", ".*")

        return f"^{pattern}"

    def _configure_allowed_origins(self, response: Response, request: Request) -> None:
        if self._allow_all_origins and not self._supports_credentials:
            # Safe+cacheable, allow everything
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif self._is_single_origin_allowed():
            # Single origins can be safely set
            response.headers["Access-Control-Allow-Origin"] = self._allowed_origins[0]
        else:
            if self.is_cors_request(request) and self.is_origin_allowed(request):
                response.headers["Access-Control-Allow-Origin"] = request.headers[
                    "Origin"
                ]

            self.vary_header(response, "Origin")

    def _is_single_origin_allowed(self) -> bool:
        if self._allow_all_origins or len(self._allowed_origins_patterns) > 0:
            return False

        return len(self._allowed_origins) == 1

    def _configure_allow_credentials(
        self, response: Response, request: Request
    ) -> None:
        if self._supports_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"

    def _configure_allowed_methods(self, response: Response, request: Request) -> None:
        if self._allow_all_methods:
            allow_methods = request.headers.get(
                "Access-Control-Request-Method", ""
            ).upper()
            self.vary_header(response, "Access-Control-Request-Method")
        else:
            allow_methods = ", ".join(self._allowed_methods).upper()

        response.headers["Access-Control-Allow-Methods"] = allow_methods

    def _configure_allowed_headers(self, response: Response, request: Request) -> None:
        if self._allow_all_headers:
            allow_headers = request.headers.get("Access-Control-Request-Headers", "")
            self.vary_header(response, "Access-Control-Request-Headers")
        else:
            allow_headers = ", ".join(self._allowed_headers)

        response.headers["Access-Control-Allow-Headers"] = allow_headers

    def _configure_max_age(self, response: Response, request: Request) -> None:
        if self._max_age is not None:
            response.headers["Access-Control-Max-Age"] = str(self._max_age)

    def _configure_exposed_headers(self, response: Response, request: Request) -> None:
        if self._exposed_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(
                self._exposed_headers
            )


class ManageCors(Middleware):
    def __init__(self, container: Container) -> None:
        self._container: Container = container
        self._cors: Cors = Cors()

    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        """
        Handle the incoming request.
        """
        if not (await self._has_matching_path(request)):
            return await next_call(request)

        self._cors.set_options(**(await self._container.make(Config)).get("cors", {}))

        if self._cors.is_preflight_request(request):
            response = self._cors.handle_preflight_request(request)

            self._cors.vary_header(response, "Access-Control-Request-Method")

            return response

        response = await next_call(request)

        if request.method == "OPTIONS":
            self._cors.vary_header(response, "Access-Control-Request-Method")

        self._cors.add_actual_request_headers(response, request)

        return response

    async def _has_matching_path(self, request: Request) -> bool:
        paths: list[str] = (
            (await self._container.make(Config)).get("cors", {}).get("paths", [])
        )

        for path in paths:
            if path != "/":
                path = path.lstrip("/")

            if request.url.is_(path) or request.url.path_is(path):
                return True

        return False


__all__ = ["ManageCors"]
