from typing import Annotated
from typing import Literal

from pydantic import AnyUrl
from pydantic import BaseModel
from pydantic import Field
from pydantic import RootModel


class ConstantBackoffConfig(BaseModel):
    strategy: Literal["constant"] = "constant"
    backoff: int = 1


class GenericBackoffConfig(BaseModel):
    strategy: Literal[
        "exponential",
        "full_jitter",
        "equal_jitter",
        "decorrelated_jitter",
        "exponential_with_jitter",
    ] = "decorrelated_jitter"
    base: int = 1
    cap: int = 10


class BackoffConfig(RootModel[ConstantBackoffConfig | GenericBackoffConfig]):
    root: Annotated[
        ConstantBackoffConfig | GenericBackoffConfig,
        Field(discriminator="strategy"),
    ]


class RedisConfig(BaseModel):
    url: AnyUrl
    cluster: bool = False
    max_retries: int = 3
    backoff: BackoffConfig | None = BackoffConfig(root=GenericBackoffConfig())
