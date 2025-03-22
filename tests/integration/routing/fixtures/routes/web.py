from expanse.contracts.routing.registrar import Registrar
from expanse.http.response import Response


def handler() -> Response:
    return Response("Hello, world!")


def routes(router: Registrar) -> None:
    router.get("/", handler)
