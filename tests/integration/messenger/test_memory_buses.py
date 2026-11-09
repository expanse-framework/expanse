from expanse.contracts.messenger.asynchronous.message_bus import MessageBus
from expanse.core.application import Application
from expanse.messenger.transports.transport_manager import TransportManager
from tests.integration.messenger.fixtures.messages import DatabaseMessage


async def test_independent_scopes_do_not_share_memory_queues(app: Application) -> None:
    app.config["messenger"] = {
        "transport": "memory",
        "transports": {"memory": {"driver": "memory"}},
    }
    async with app.container.create_scoped_container() as first:
        await (await first.get(MessageBus)).dispatch(DatabaseMessage(value="first"))
        async with app.container.create_scoped_container() as second:
            receiver = await (await second.get(TransportManager)).receiver("memory")
            assert [message async for message in receiver.receive()] == []
        receiver = await (await first.get(TransportManager)).receiver("memory")
        messages = [message async for message in receiver.receive()]
        assert [message.open().value for message in messages] == ["first"]
