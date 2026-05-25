from expanse.core.application import Application


async def test_cache_service_provider_registers_commands(app: Application):
    from expanse.core.console.portal import Portal

    portal = await app.container.get(Portal)
    console = portal.console

    assert console.has("make cache table")
