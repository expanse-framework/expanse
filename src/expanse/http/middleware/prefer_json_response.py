from expanse.http.request import Request
from expanse.http.responses.response import Response
from expanse.types.http.middleware import RequestHandler


class PreferJsonResponse:
    async def handle(self, request: Request, next_call: RequestHandler) -> Response:
        accept = request.headers.get("accept")
        if not accept:
            request.prefer_response_format("application/json")
        else:
            acceptable_formats = request.acceptable_content_types
            if acceptable_formats and acceptable_formats[0] in (
                "*",
                "*/*",
                "application/*",
            ):
                request.prefer_response_format("application/json")

        return await next_call(request)
