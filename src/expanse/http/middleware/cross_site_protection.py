from expanse.http.helpers import abort
from expanse.http.request import Request
from expanse.http.response import Response
from expanse.http.url import URL
from expanse.types.http.middleware import RequestHandler


class CrossSitePolicy:
    def __init__(self, allow_safe_methods: bool = True) -> None:
        self._allow_safe_methods: bool = allow_safe_methods

    def allow(self, request: Request) -> bool:
        if self._allow_safe_methods and request.method in {"GET", "HEAD", "OPTIONS"}:
            return True

        fetch_site = request.headers.get("Sec-Fetch-Site", "").lower().strip()

        match fetch_site:
            case "":
                # No Sec-Fetch-Site header
                # We will fallback on an origin check later
                pass

            case "same-origin" | "none":
                return True

            case _:
                return False

        origin = request.headers.get("Origin", "")
        if not origin:
            # Neither Sec-Fetch-Site nor origin headers are present.
            # Either the request does not originate from a browser or the browser is too old.
            return True

        origin_url = URL(origin)

        # The Origin header matches the Host header
        return origin_url.hostname == request.host


class CrossSiteProtection:
    _allow_safe_methods: bool = True

    async def handle(self, request: Request, next: RequestHandler) -> Response:
        policy = CrossSitePolicy(allow_safe_methods=self._allow_safe_methods)

        if not policy.allow(request):
            abort(403)

        return await next(request)
