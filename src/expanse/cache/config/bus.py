from pydantic import BaseModel


class BusConfig(BaseModel):
    # The name of messenger transport that should be used for the cache bus.
    # The value must match one of the configured messenger transports.
    transport: str = "default"
