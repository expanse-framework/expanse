from expanse.contracts.routing.router import Router
from expanse.testing.command_tester import CommandTester


async def post_endpoint() -> str:
    return ""


async def delete_endpoint() -> str:
    return ""


async def test_route_listing(command_tester: CommandTester, router: Router) -> None:
    router.post("/post", post_endpoint)
    with router.group("group", prefix="/group") as group:
        group.delete("/delete", delete_endpoint, name="delete_name")

    command = command_tester.command("routes list")

    assert command.run() == 0

    expected_output = """
  DELETE  /group/delete (group.delete_name)
  POST    /post
  GET     /static/{*path} (static)
"""
    assert command.output.fetch() == expected_output


async def test_route_listing_verbose(
    command_tester: CommandTester, router: Router
) -> None:
    router.post("/post", post_endpoint)
    with router.group("group", prefix="/group") as group:
        group.delete("/delete", delete_endpoint, name="delete_name")

    command = command_tester.command("routes list")

    assert command.run("-v") == 0

    expected_output = f"""
  DELETE  /group/delete (group.delete_name)
          {delete_endpoint.__module__}.delete_endpoint
  POST    /post
          {post_endpoint.__module__}.post_endpoint
  GET     /static/{{*path}} (static)
          expanse.static.static.Static.get
"""
    assert command.output.fetch() == expected_output
