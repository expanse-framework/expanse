from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.messenger.asynchronous.transport_manager import TransportManager
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry
from expanse.messenger.retry.config import RetryStrategyConfig
from expanse.messenger.retry.multiplier.config import MultiplierRetryStrategyConfig
from expanse.messenger.retry.retry_strategy import RetryStrategy
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)
from expanse.support.asynchronous.pipeline import Pipeline


class Worker:
    def __init__(
        self,
        transport_manager: TransportManager,
        config: Config,
        middleware_stack: MiddlewareStack,
        container: Container,
        registry: Registry,
    ) -> None:
        self._transport_manager: TransportManager = transport_manager
        self._config: Config = config
        self._middleware_stack: MiddlewareStack = middleware_stack
        self._container: Container = container
        self._registry: Registry = registry
        self._should_stop: bool = False

    async def run(
        self, transport_name: str | None = None, limit: int | None = None
    ) -> None:
        """
        Run the worker, processing messages from the bus until stopped.
        """
        self._should_stop = False

        transport = self._transport_manager.transport(transport_name)

        handled_messages = 0
        while not self._should_stop:
            if handled_messages >= limit if limit is not None else False:
                self.stop()
                continue

            envelope = await transport.receive()

            if envelope is None:
                continue

            handled_messages += 1

            try:
                await self._process_envelope(envelope)
            except UnrecoverableMessageHandlingError:
                # The message handling error is unrecoverable, we don't want to retry it.
                # If a failure transport is configured, we send the message to the failure transport
                # for further analysis.
                await self._send_to_failure_transport(
                    envelope, transport_name=transport_name
                )
                await transport.reject(envelope)
            except Exception as e:
                # Check if the message should be retried according to the transport's retry strategy.
                # If it should, we send it to the same transport with the configured delay.
                # If it shouldn't, we send it to the failure transport if configured, or discard it otherwise.
                retry_strategy = self._get_retry_strategy(transport_name)

                if retry_strategy is None:
                    # If no retry strategy is configured for the transport,
                    # we consider that the message shouldn't be retried.
                    await self._send_to_failure_transport(
                        envelope, transport_name=transport_name
                    )
                    await transport.reject(envelope)
                    continue

                if not retry_strategy.should_retry(envelope, e):
                    await self._send_to_failure_transport(
                        envelope, transport_name=transport_name
                    )
                    await transport.reject(envelope)
                    continue

                delay = retry_strategy.retry_delay(envelope, e)
                redelivery_stamp = envelope.stamp(RedeliveryStamp)
                retry_count = (
                    redelivery_stamp.retry_count if redelivery_stamp is not None else 0
                ) + 1
                await transport.send(
                    envelope.with_stamps(
                        DelayStamp(delay), RedeliveryStamp(retry_count=retry_count)
                    )
                )

                await transport.reject(envelope)

                continue

            await transport.acknowledge(envelope)

    def stop(self) -> None:
        """
        Stop the worker gracefully.
        """
        self._should_stop = True

    async def _process_envelope(self, envelope: Envelope) -> Envelope:
        pipeline = Pipeline[Envelope, Envelope]()
        pipeline.use(
            [
                (await self._container.get(m)).handle
                for m in self._middleware_stack.middleware
            ]
        )

        return await pipeline.send(envelope.with_stamps(ReceivedStamp())).to(
            self._handle_envelope
        )

    async def _handle_envelope(self, envelope: Envelope) -> Envelope:
        message = envelope.open()
        handlers = self._registry.get_handlers(message.__class__)

        for handler in handlers:
            await self._container.call(handler, message)

        return envelope

    async def _send_to_failure_transport(
        self, envelope: Envelope, transport_name: str
    ) -> None:
        failure_transport_name = self._config.get("messenger.failure_transport")
        if not failure_transport_name:
            return

        failure_transport = self._transport_manager.transport(failure_transport_name)
        await failure_transport.send(
            envelope.with_stamps(
                SentToFailureTransportStamp(original_transport=transport_name),
                DelayStamp(delay=0),
                RedeliveryStamp(retry_count=0),
            )
        )

    def _get_retry_strategy(self, transport_name: str) -> RetryStrategy | None:
        retry_strategy_alias = self._config.get(
            f"messenger.transports.{transport_name}", {}
        ).get("retry_strategy")

        if retry_strategy_alias is None:
            return None

        if retry_strategy_alias not in self._config.get(
            "messenger.retry_strategies", {}
        ):
            # TODO: log an error
            return None

        config = RetryStrategyConfig.model_validate(
            self._config.get(f"messenger.retry_strategies.{retry_strategy_alias}", {})
        ).root

        match config:
            case MultiplierRetryStrategyConfig():
                from expanse.messenger.retry.multiplier.multiplier_retry_strategy import (
                    MultiplierRetryStrategy,
                )

                return MultiplierRetryStrategy(config)
