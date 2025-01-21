import json
from datetime import datetime, timezone
from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field
from syft_core.types import PathLike, to_path
from syft_core.url import SyftBoxURL
from typing_extensions import Self
from ulid import ULID


class SyftMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class SyftStatus(IntEnum):
    SYFT_200_OK = 200
    SYFT_201_CREATED = 201


class SyftMessage(BaseModel):
    version: int = 1
    ulid: ULID = Field(default_factory=ULID)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires: datetime
    sender: str
    url: SyftBoxURL
    headers: dict[str, str]
    body: bytes | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def dump(self) -> str:
        """
        Serialize the model instance to JSON format.
        """
        return self.model_dump_json()

    @classmethod
    def load(cls, data: bytes) -> Self:
        """
        Deserialize JSON data into a model instance.
        """
        obj = json.loads(data)
        return cls.model_validate(obj)

    @classmethod
    def from_path(cls, path: PathLike) -> Self:
        """
        Load a model instance from a file path.
        """
        file_path = to_path(path)
        return cls.load(file_path.read_bytes())


class SyftRequest(SyftMessage):
    method: SyftMethod = SyftMethod.GET


class SyftResponse(SyftMessage):
    status_code: SyftStatus = SyftStatus.SYFT_200_OK


class SyftFuture(BaseModel):
    ulid: ULID
    url: SyftBoxURL
    status: SyftStatus = SyftStatus.SYFT_201_CREATED

    model_config = ConfigDict(arbitrary_types_allowed=True)
