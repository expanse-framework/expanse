from collections.abc import Awaitable
from collections.abc import Callable
from typing import ClassVar

from expanse.contracts.rate_limiting.rate_limit import RateLimit
from expanse.core.http.exceptions import HTTPException
from expanse.http.request import Request
from expanse.http.responses.response import Response
from expanse.rate_limiting.rate_limiting_manager import RateLimitingManager
from expanse.support._concurrency import run_async
from expanse.support.helpers import async_safe
from expanse.types.http.middleware import RequestHandler


type KeyResolver = Callable[[Request], str] | Callable[[Request], Awaitable[str]]


@async_safe()
def _default_key_resolver(request: Request) -> str:
    parts = [request.ip or "unknown", request.url.path, request.method]

    return "|".join(parts)


class ThrottleRequest:
    _limiter: str = ""
    _key_resolver: ClassVar[KeyResolver] = _default_key_resolver

    def __init__(self, rate_limiting_manager: RateLimitingManager) -> None:
        self._rate_limiting_manager: RateLimitingManager = rate_limiting_manager

    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        limiter = await self._rate_limiting_manager.limiter(self._limiter)

        key = await run_async(self.__class__._key_resolver, request)

        rate_limit = await limiter.consume(key)

        if not rate_limit.accepted:
            raise self._build_rate_limit_exception(rate_limit)

        response = await next_call(request)

        response.with_headers(
            {
                "X-RateLimit-Limit": str(rate_limit.limit),
                "X-RateLimit-Remaining": str(rate_limit.available_tokens),
                "X-RateLimit-Reset": str(rate_limit.retry_after.timestamp()),
            }
        )

        return response

    @classmethod
    def using(
        cls, limiter: str, key_resolver: KeyResolver | None = None
    ) -> type["ThrottleRequest"]:
        key_resolver = key_resolver or _default_key_resolver

        subcls = type(
            f"ThrottleRequest[{limiter!r}, {key_resolver!r}]",
            (cls,),
            {
                "_limiter": limiter,
                "_key_resolver": key_resolver,
            },
        )

        return subcls

    def _build_rate_limit_exception(self, rate_limit: RateLimit) -> Exception:
        return HTTPException(
            429,
            "Max attempts exceeded.",
            headers={
                "X-RateLimit-Limit": str(rate_limit.limit),
                "X-RateLimit-Remaining": str(rate_limit.available_tokens),
                "X-RateLimit-Reset": str(rate_limit.retry_after.timestamp()),
                "Retry-After": rate_limit.retry_after.format_rfc2822(),
            },
        )
