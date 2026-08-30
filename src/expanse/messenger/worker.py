import asyncio
import contextvars
import itertools
import logging

from enum import StrEnum
from typing import Any

from expanse.configuration.config import Config
from expanse.container.container import Container
from expanse.contracts.cache.asynchronous.cache import Cache
from expanse.contracts.messenger.asynchronous.keep_alive_transport import (
    KeepAliveTransport,
)
from expanse.contracts.messenger.asynchronous.transport import Transport
from expanse.contracts.messenger.asynchronous.worker_aware_transport import (
    WorkerAwareTransport,
)
from expanse.encryption.utils import generate_random_string
from expanse.jobs.asynchronous.job import Job as AsyncJob
from expanse.jobs.stamps.job import JobStamp
from expanse.jobs.synchronous.job import Job as SyncJob
from expanse.logging.context import Context
from expanse.messenger.envelope import Envelope
from expanse.messenger.exceptions import MessageHandlingFailedError
from expanse.messenger.exceptions import UnconfiguredRetryStrategyError
from expanse.messenger.exceptions import UnrecoverableMessageHandlingError
from expanse.messenger.exceptions import UnsupportedRetryStrategyError
from expanse.messenger.locks.unique import UniqueLock
from expanse.messenger.middleware.middleware_stack import MiddlewareStack
from expanse.messenger.registry import Registry
from expanse.messenger.retry.retry_strategy import RetryStrategy
from expanse.messenger.retry.retry_strategy_manager import RetryStrategyManager
from expanse.messenger.stamps.delay import DelayStamp
from expanse.messenger.stamps.handled import HandledStamp
from expanse.messenger.stamps.received import ReceivedStamp
from expanse.messenger.stamps.redelivery import RedeliveryStamp
from expanse.messenger.stamps.sent_to_failure_transport import (
    SentToFailureTransportStamp,
)
from expanse.messenger.stamps.transport_message_id import TransportMessageIdStamp
from expanse.messenger.stamps.unique import UniqueStamp
from expanse.messenger.transports.transport_manager import TransportManager
from expanse.support._utils import string_to_class
from expanse.support.asynchronous.pipeline import Pipeline
from expanse.types.messenger import MessageHandler


logger = logging.getLogger(__name__)


class MessageLogMessage(StrEnum):
    HANDLED = "Message %s handled successfully."
    UNRECOVERABLE_ERROR = "Message handling failed with an unrecoverable error, removing from transport. Error: %s"
    FAILED_AFTER_RETRIES = "Message handling failed after %s retries. Error: %s"
    FAILED = "Message handling failed. Error: %s"
    FAILED_RETRYING = (
        "Message handling failed, sending for retry %s with a delay of %ss. Error: %s"
    )
    SKIPPED_DUPLICATE = (
        "Skipping message that is already being processed by this worker."
    )


class JobLogMessage(StrEnum):
    HANDLED = "Job %s executed successfully."
    UNRECOVERABLE_ERROR = "Job failed with an unrecoverable error. Error: %s"
    FAILED_AFTER_RETRIES = "Job failed after %s retries. Error: %s"
    FAILED = "Job failed. Error: %s"
    FAILED_RETRYING = "Job failed, sending for retry %s with a delay of %ss. Error: %s"
    SKIPPED_DUPLICATE = "Skipping job that is already being processed by this worker."


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
        self._keep_alives: dict[int, tuple[str, Envelope]] = {}
        self._keep_alive_ids: itertools.count[int] = itertools.count()
        # Transport message IDs currently being processed by one of this
        # worker's own consumer slots. A lease-based transport (database,
        # redis, ...) may consider a message eligible for redelivery again
        # once its lease expires, even though a sibling slot in this same
        # process is still actively handling it (e.g. its keep-alive
        # refresh hasn't run yet); this guards against reprocessing it in
        # that case, without affecting redelivery to *other* worker
        # processes, which is the mechanism's intended purpose.
        self._in_flight_message_ids: set[tuple[str, Any]] = set()

    async def run(
        self,
        transport_name: str | None = None,
        limit: int | None = None,
        sleep: int = 1000,
        concurrency: int = 1,
    ) -> None:
        """
        Run the worker, processing messages from the bus until stopped.

        When `concurrency` is greater than 1, `concurrency` independent
        consumer loops run concurrently, all pulling from the same transport.
        """
        self._stop_event.clear()

        if transport_name is None:
            transport_name = self._transport_manager.get_default_transport_name()

        transport = await self._transport_manager.transport(transport_name)

        handled_messages = 0
        handled_lock = asyncio.Lock()

        async def reserve_slot() -> bool:
            nonlocal handled_messages

            async with handled_lock:
                if limit is not None and handled_messages >= limit:
                    return False

                handled_messages += 1

                return True

        async def consume(concurrent: bool = True) -> None:
            worker_transport = transport

            if concurrent:
                worker_id = generate_random_string(8, restricted=True)
                context = await self._container.get(Context)
                context["worker.id"] = worker_id

                if isinstance(transport, WorkerAwareTransport):
                    worker_transport = transport.clone_for_worker(worker_id)

            while not self._stop_event.is_set():
                if limit is not None and handled_messages >= limit:
                    self.stop()
                    continue

                envelope_handled: bool = False

                async for envelope in worker_transport.receive():
                    envelope_handled = True

                    if not await reserve_slot():
                        self.stop()
                        break

                    await self._process_envelope(
                        envelope, worker_transport, transport_name
                    )

                if not envelope_handled:
                    await asyncio.sleep(sleep / 1000)

        if concurrency <= 1:
            await consume(False)
        else:
            await asyncio.gather(*(consume() for _ in range(concurrency)))

    async def _process_envelope(
        self, envelope: Envelope, transport: Transport, transport_name: str
    ) -> None:
        keep_alive_id = next(self._keep_alive_ids)
        dedup_key: tuple[str, Any] | None = None
        log_messages: type[MessageLogMessage] | type[JobLogMessage]
        message_id_stamp = envelope.stamp(TransportMessageIdStamp)
        log_extras: dict[str, Any] = {
            "transport": transport_name,
        }
        if message_id_stamp is not None:
            log_extras["message_id"] = message_id_stamp.id

        if job_stamp := envelope.stamp(JobStamp):
            log_extras["job"] = job_stamp.job
            log_messages = JobLogMessage
        else:
            log_extras["message_type"] = envelope.open().__class__.__name__
            log_messages = MessageLogMessage

        if isinstance(transport, KeepAliveTransport):
            message_id_stamp = envelope.stamp(TransportMessageIdStamp)
            if message_id_stamp is not None:
                dedup_key = (transport_name, message_id_stamp.id)

            if dedup_key is not None and dedup_key in self._in_flight_message_ids:
                # Another one of this worker's own slots is already
                # processing this exact message: skip it rather than
                # handling it a second time.
                logger.debug(log_messages.SKIPPED_DUPLICATE.value, extra=log_extras)

                return

            if dedup_key is not None:
                self._in_flight_message_ids.add(dedup_key)

            self._keep_alives[keep_alive_id] = (transport_name, envelope)

        try:
            envelope = await self._handle_envelope(envelope)
        except Exception as e:
            if isinstance(e, MessageHandlingFailedError):
                envelope = e.envelope

                if any(
                    isinstance(error, UnrecoverableMessageHandlingError)
                    for error in e.errors.values()
                ):
                    logger.error(
                        log_messages.UNRECOVERABLE_ERROR.value,
                        e,
                        extra={
                            **log_extras,
                            "error": str(e),
                        },
                    )
                    # If any of the errors are unrecoverable, we consider the message as not handled and send it to the failure transport if configured.
                    await self._send_to_failure_transport(
                        e.envelope, transport_name=transport_name
                    )
                    await transport.reject(e.envelope)

                    self._keep_alives.pop(keep_alive_id, None)
                    self._in_flight_message_ids.discard(dedup_key)

                    await self._release_unique_lock(envelope)

                    return

            # If there were errors during message handling, we consider the message as not handled.
            # If the message can and should be retried we send it back to the same transport with the appropriate delay.
            # Otherwise, if a failure transport is configured, we send it to the failure transport for further analysis.
            retry_strategy = self._get_retry_strategy(transport_name)
            if retry_strategy is None or not retry_strategy.should_retry(
                envelope, exception=e
            ):
                error_message: str
                error_message_args: list[Any] = []
                redelivery_stamp = envelope.stamp(RedeliveryStamp)

                if redelivery_stamp is not None:
                    error_message = log_messages.FAILED_AFTER_RETRIES.value
                    error_message_args.append(redelivery_stamp.retry_count)
                else:
                    error_message = log_messages.FAILED.value

                error_message_args.append(e)

                logger.error(
                    error_message,
                    *error_message_args,
                    extra={
                        **log_extras,
                        "error": str(e),
                    },
                )
                await self._send_to_failure_transport(
                    envelope, transport_name=transport_name
                )
                await transport.reject(envelope)

                self._keep_alives.pop(keep_alive_id, None)
                self._in_flight_message_ids.discard(dedup_key)

                await self._release_unique_lock(envelope)

                return

            delay = retry_strategy.retry_delay(envelope, e)
            redelivery_stamp = envelope.stamp(RedeliveryStamp)
            retry_count = (
                redelivery_stamp.retry_count if redelivery_stamp is not None else 0
            ) + 1
            logger.warning(
                log_messages.FAILED_RETRYING.value,
                retry_count,
                delay,
                e,
                extra={
                    **log_extras,
                    "error": str(e),
                },
            )
            await transport.send(
                envelope.with_stamps(
                    DelayStamp(delay), RedeliveryStamp(retry_count=retry_count)
                )
            )

            await transport.reject(envelope)

            self._keep_alives.pop(keep_alive_id, None)
            self._in_flight_message_ids.discard(dedup_key)

            return

        logger.info(
            log_messages.HANDLED.value,
            log_extras.get("job", log_extras.get("message_type")),
            extra=log_extras,
        )

        await transport.acknowledge(envelope)

        self._keep_alives.pop(keep_alive_id, None)
        self._in_flight_message_ids.discard(dedup_key)

    def stop(self) -> None:
        """
        Stop the worker gracefully.
        """
        logger.info("Stopping worker.")

        self._stop_event.set()

    async def keep_alive(self, duration: int | None = None) -> None:
        """
        Keep the worker alive until stopped.
        """
        # Snapshot before iterating: concurrent slots may insert/pop envelopes
        # into `self._keep_alives` while we `await` below.
        for transport_name, envelope in list(self._keep_alives.values()):
            transport = await self._transport_manager.transport(transport_name)

            if not isinstance(transport, KeepAliveTransport):
                raise RuntimeError(
                    f"Transport '{transport_name}' does not support keep-alive functionality."
                )

            logger.debug(
                "Keeping message alive",
                extra={
                    "transport": transport_name,
                    "message_id": stamp.id
                    if (stamp := envelope.stamp(TransportMessageIdStamp)) is not None
                    else None,
                },
            )

            await transport.keep_alive(envelope, duration)

    async def _handle_envelope(self, envelope: Envelope) -> Envelope:
        # Each envelope is handled with its own scoped container so that
        # concurrently-processed messages never share resolved instances.
        container = self._container.create_scoped_container()

        try:
            message = envelope.open()
            container.instance(message.__class__, message)

            async def _handle(envelope: Envelope) -> Envelope:
                message = envelope.open()
                errors: dict[str, Exception] = {}
                if stamp := envelope.stamp(JobStamp):
                    # If the envelope is marked with the JobStamp,
                    # we skip the registry and handle it directly.
                    job_class = string_to_class(stamp.job)
                    if not (
                        isinstance(job_class, type)
                        and issubclass(job_class, SyncJob | AsyncJob)
                    ):
                        # Checked before instantiation: `stamp.job` names a class
                        # resolved from message data, so construct it only once
                        # we know it's actually a Job.
                        raise TypeError(
                            f"Expected job of type 'Job', got '{job_class!r}'"
                        )
                    job = job_class(message)

                    try:
                        token = self._isolate_log_context()
                        try:
                            await container.call(job.execute)
                        finally:
                            self._restore_log_context(token)

                        envelope = envelope.with_stamps(
                            HandledStamp(
                                handler=f"{job_class.__module__}.{job_class.__qualname__}.execute"
                            )
                        )
                    except Exception as e:
                        errors[
                            f"{job_class.__module__}.{job_class.__qualname__}.execute"
                        ] = e

                    if errors:
                        raise MessageHandlingFailedError(
                            envelope=envelope, errors=errors
                        )

                    return envelope

                handlers = self._registry.get_handlers(message.__class__)

                for handler in handlers:
                    if self._has_already_been_handled(envelope, handler):
                        continue

                    try:
                        token = self._isolate_log_context()
                        try:
                            await container.call(handler, message)
                        finally:
                            self._restore_log_context(token)

                        envelope = envelope.with_stamps(
                            HandledStamp(
                                handler=f"{handler.__module__}.{handler.__qualname__}"
                            )
                        )
                    except Exception as e:
                        errors[f"{handler.__module__}.{handler.__qualname__}"] = e

                if errors:
                    raise MessageHandlingFailedError(envelope=envelope, errors=errors)

                return envelope

            # Build the middleware pipeline and process the envelope through it.
            # We need to reverse the middleware stack to ensure messages are properly
            # processed. For instance, if messages with a context to propagate have been
            # encrypted, we need to decrypt them first.
            return await (
                Pipeline[Envelope, Envelope]()
                .use(
                    [
                        (await container.get(m)).handle
                        for m in self._middleware_stack.middleware[::-1]
                    ]
                )
                .send(envelope.with_stamps(ReceivedStamp()))
                .to(_handle)
                .then(self._after_handling_envelope)
                .run()
            )
        finally:
            # A failure while tearing down scoped dependencies (e.g. closing
            # a database session) must not be mistaken for the message
            # handling itself having failed: the job/handler above may have
            # already completed successfully, and letting a termination
            # error propagate here would cause the worker to retry
            # a message that already ran successfully.
            try:
                await container.terminate()
            except Exception:
                logger.exception(
                    "Error while terminating the scoped container for message %s",
                    envelope.open().__class__.__name__,
                )

    async def _after_handling_envelope(self, envelope: Envelope) -> None:
        await self._release_unique_lock(envelope)

    async def _release_unique_lock(self, envelope: Envelope) -> None:
        if envelope.has_stamp(UniqueStamp):
            # The unique lock is backed by the shared `Cache` service, not
            # per-envelope scoped state, so the base container is used here
            # (the scoped container from `_handle_envelope` may already be
            # torn down by the time this runs from an error path).
            await UniqueLock(await self._container.get(Cache)).release(envelope)

    def _has_already_been_handled(
        self, envelope: Envelope, handler: MessageHandler[Any]
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
        logger.info(
            "Sending rejected message to failure transport: %s",
            failure_transport_name,
            extra={
                "message_type": envelope.open().__class__.__name__,
                "failure_transport": failure_transport_name,
            },
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

    def _isolate_log_context(self) -> contextvars.Token[Any]:
        from expanse.logging.context import Context
        from expanse.logging.utils import _context

        original = _context.get() or Context()
        return _context.set(Context(**original))

    def _restore_log_context(self, token: contextvars.Token[Any]) -> None:
        from expanse.logging.utils import _context

        _context.reset(token)
