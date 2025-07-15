from treat.mock import Mockery

from expanse.container.container import Container
from expanse.contracts.routing.router import Router
from expanse.core.application import Application
from expanse.core.http.portal import Portal
from expanse.http.request import Request
from expanse.http.response import Response


async def test_portal_prepares_response_before_sending_it_back(
    app: Application, router: Router, mockery: Mockery
) -> None:
    router.get("/", lambda: "Foo")

    request = Request.create("http://localhost:8000/")

    container = Container()
    mockery.mock(Container).should_receive("create_scoped_container").and_return(
        container
    )
    mockery.mock(Response).should_receive("prepare").with_(request, container).times(1)

    portal = Portal(app, router)

    response = await portal.handle(request)

    assert response.status_code == 200
