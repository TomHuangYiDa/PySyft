import json
from datetime import datetime, timezone
from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field
from syft_core.url import SyftBoxURL
from ulid import ULID


class SyftMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


class SyftStatus(IntEnum):
    SYFT_200_OK = 200


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
    def load(cls, data: bytes):
        """
        Deserialize JSON data into a model instance.
        """
        obj = json.loads(data)
        return cls.model_validate(obj)


class SyftRequest(SyftMessage):
    method: SyftMethod = SyftMethod.GET


class SyftResponse(SyftMessage):
    status_code: SyftStatus = SyftStatus.SYFT_200_OK


class SyftFuture(BaseModel):
    request_path: SyftBoxURL
