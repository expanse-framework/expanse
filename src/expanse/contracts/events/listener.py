from expanse.contracts.events.asynchronous.listener import AsyncEventListener
from expanse.contracts.events.synchronous.listener import (
    EventListener as SyncEventListener,
)


type EventListener[Event] = AsyncEventListener[Event] | SyncEventListener[Event]
