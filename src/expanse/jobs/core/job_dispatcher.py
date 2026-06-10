from typing import Any

from expanse.jobs.core.job import Job
from expanse.jobs.stamps.job import JobStamp
from expanse.messenger.envelope import Envelope
from expanse.support._utils import class_to_name
from expanse.types.messenger import Stamp


class JobDispatcher:
    def prepare(self, job: Job[Any]) -> Envelope:
        """
        Prepare a job for dispatching by converting it into an envelope.

        :param job: The job to prepare for dispatching.

        :return: An Envelope instance that wraps the job and can be used for dispatching.
        """
        stamps = self._get_stamps_for_job(job)
        payload = job.payload

        return Envelope(payload, stamps)

    def _get_stamps_for_job(self, job: Job[Any]) -> list[Stamp]:
        """
        Retrieve the list of stamps associated with a job.

        :param job: The job for which to retrieve stamps.

        :return: A list of Stamp instances associated with the job.
        """
        # Convert job options into stamps.
        stamps: list[Stamp] = [JobStamp(class_to_name(job.__class__))]

        if not job.options:
            return stamps

        if "delay" in job.options:
            from expanse.messenger.stamps.delay import DelayStamp

            delay = job.options["delay"]

            stamps.append(DelayStamp(delay * 1000))

        if "transport" in job.options:
            from expanse.messenger.stamps.transport import TransportStamp

            transport = job.options["transport"]

            stamps.append(TransportStamp(transport))

        return stamps
