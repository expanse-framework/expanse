from pydantic import BaseModel


class RedisBusConfig(BaseModel):
    connection: str

    channel: str = "expanse:cache:notifications"
