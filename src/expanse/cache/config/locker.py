from pydantic import BaseModel


class LockerConfig(BaseModel):
    store: str
