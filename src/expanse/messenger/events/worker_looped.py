from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkerLooped:
    transport: str
