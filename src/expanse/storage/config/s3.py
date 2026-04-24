from typing import Literal

from pydantic import BaseModel


class S3StorageConfig(BaseModel):
    driver: Literal["s3"] = "s3"

    key: str
    secret: str
    region: str | None = None
    bucket: str
    endpoint: str | None = None
