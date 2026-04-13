import asyncio

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageHandlingFailedError
from expanse.messenger.exceptions import SelfHandlingMessageWithNoHandlerError
from expanse.messenger.exceptions import UnconfiguredRetryStrategyError
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.exceptions import UnsupportedRetryStrategyError
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry
from expanse.messenger.retry.retry_strategy import RetryStrategy
from expanse.messenger.retry.retry_strategy_manager import RetryStrategyManager
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.handled import HandledStamp
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.self_handling import SelfHandlingStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)
from expanse.messenger.transports.transport_manager import TransportManager
from expanse.support.asynchronous.pipeline import Pipeline
from expanse.types.messenger import MessageHandler


class Worker:
    def __init__(
        self,
        transport_manager: TransportManager,
        retry_strategy_manager: RetryStrategyManager,
        config: Config,
        middleware_stack: MiddlewareStack,
        container: Container,
        registry: Registry,
    ) -> None:
        self._transport_manager: TransportManager = transport_manager
        self._retry_strategy_manager: RetryStrategyManager = retry_strategy_manager
        self._config: Config = config
        self._middleware_stack: MiddlewareStack = middleware_stack
        self._container: Container = container
        self._registry: Registry = registry
        self._stop_event: asyncio.Event = asyncio.Event()

    async def run(
        self,
        transport_name: str | None = None,
        limit: int | None = None,
        sleep: int = 1000,
    ) -> None:
        """
        Run the worker, processing messages from the bus until stopped.
        """
        self._stop_event.clear()

        if transport_name is None:
            transport_name = self._transport_manager.get_default_transport_name()

        transport = await self._transport_manager.transport(transport_name)

        handled_messages = 0
        while not self._stop_event.is_set():
            if handled_messages >= limit if limit is not None else False:
                self.stop()
                continue

            envelope_handled: bool = False

            async for envelope in transport.receive():
                envelope_handled = True
                if handled_messages >= limit if limit is not None else False:
                    self.stop()
                    break

                handled_messages += 1

                try:
                    envelope = await self._handle_envelope(envelope)
                except Exception as e:
                    if isinstance(e, MessageHandlingFailedError):
                        envelope = e.envelope

                        if any(
                            isinstance(error, UnrecoverableMessageHandlingError)
                            for error in e.errors.values()
                        ):
                            # If any of the errors are unrecoverable, we consider the message as not handled and send it to the failure transport if configured.
                            await self._send_to_failure_transport(
                                e.envelope, transport_name=transport_name
                            )
                            await transport.reject(e.envelope)

                            continue

                    # If there were errors during message handling, we consider the message as not handled.
                    # If the message can and should be retried we send it back to the same transport with the appropriate delay.
                    # Otherwise, if a failure transport is configured, we send it to the failure transport for further analysis.
                    retry_strategy = self._get_retry_strategy(transport_name)
                    if retry_strategy is None or not retry_strategy.should_retry(
                        envelope, exception=e
                    ):
                        await self._send_to_failure_transport(
                            envelope, transport_name=transport_name
                        )
                        await transport.reject(envelope)

                        continue

                    delay = retry_strategy.retry_delay(envelope, e)
                    redelivery_stamp = envelope.stamp(RedeliveryStamp)
                    retry_count = (
                        redelivery_stamp.retry_count
                        if redelivery_stamp is not None
                        else 0
                    ) + 1
                    await transport.send(
                        envelope.with_stamps(
                            DelayStamp(delay), RedeliveryStamp(retry_count=retry_count)
                        )
                    )

                    await transport.reject(envelope)

                    continue

                await transport.acknowledge(envelope)

            if not envelope_handled:
                await asyncio.sleep(sleep / 1000)

    def stop(self) -> None:
        """
        Stop the worker gracefully.
        """
        self._stop_event.set()

    async def _handle_envelope(self, envelope: Envelope) -> Envelope:
        # Build the middleware pipeline and process the envelope through it.
        envelope = await (
            Pipeline[Envelope, Envelope]()
            .use(
                [
                    (await self._container.get(m)).handle
                    for m in self._middleware_stack.middleware
                ]
            )
            .send(envelope.with_stamps(ReceivedStamp()))
            .to(self._get_envelope)
        )

        message = envelope.open()
        errors: dict[str, Exception] = {}
        handlers: list[MessageHandler] = []
        if envelope.has_stamp(SelfHandlingStamp):
            # If the envelope is marked with the SelfHandlingStamp,
            # we skip the registry and handle it directly.
            handler = getattr(message, "handle", None)
            try:
                if handler is None or not callable(handler):
                    raise SelfHandlingMessageWithNoHandlerError(
                        "Self handling messages must have a callable 'handle' method"
                    )
                await self._container.call(handler)

                envelope = envelope.with_stamps(
                    HandledStamp(handler=f"{handler.__module__}.{handler.__qualname__}")
                )
            except Exception as e:
                if handler is not None and callable(handler):
                    errors[f"{handler.__module__}.{handler.__qualname__}"] = e
                else:
                    errors[
                        f"{type(message).__module__}.{type(message).__qualname__}.handle"
                    ] = e
        else:
            handlers = self._registry.get_handlers(message.__class__)

        for handler in handlers:
            if self._has_already_been_handled(envelope, handler):
                continue

            try:
                await self._container.call(handler, message)

                envelope = envelope.with_stamps(
                    HandledStamp(handler=f"{handler.__module__}.{handler.__qualname__}")
                )
            except Exception as e:
                errors[f"{handler.__module__}.{handler.__qualname__}"] = e

        if errors:
            raise MessageHandlingFailedError(envelope=envelope, errors=errors)

        return envelope

    async def _get_envelope(self, envelope: Envelope) -> Envelope:
        return envelope

    def _has_already_been_handled(
        self, envelope: Envelope, handler: MessageHandler
    ) -> bool:
        handler_identifier = f"{handler.__module__}.{handler.__qualname__}"
        for handled_stamp in envelope.stamps(HandledStamp):
            if handled_stamp.handler == handler_identifier:
                return True

        return False

    async def _send_to_failure_transport(
        self, envelope: Envelope, transport_name: str
    ) -> None:
        failure_transport_name = self._config.get("messenger.failure_transport")
        if not failure_transport_name:
            return

        failure_transport = await self._transport_manager.transport(
            failure_transport_name
        )
        await failure_transport.send(
            envelope.with_stamps(
                SentToFailureTransportStamp(original_transport=transport_name),
                DelayStamp(delay=0),
                RedeliveryStamp(retry_count=0),
            )
        )

    def _get_retry_strategy(self, transport_name: str) -> RetryStrategy | None:
        retry_strategy_alias: str | None = self._config.get(
            f"messenger.transports.{transport_name}", {}
        ).get("retry_strategy")

        if retry_strategy_alias is None:
            return None

        try:
            return self._retry_strategy_manager.strategy(retry_strategy_alias)
        except (UnconfiguredRetryStrategyError, UnsupportedRetryStrategyError):
            return None
