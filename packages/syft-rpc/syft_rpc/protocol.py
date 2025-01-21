import json
from datetime import datetime, timezone
from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator
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


class Base(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def dumps(self) -> str:
        """
        Serialize the model instance to JSON formatted ``str``.
        """
        return self.model_dump_json()

    def dump(self, path: PathLike) -> str:
        """
        Serialize the model instance as a JSON formatted stream to the file at ``path``.
        """
        return path.write_text(self.dumps())

    @classmethod
    def loads(cls, s: str | bytes | bytearray) -> Self:
        """
        Load a model instance from ``s`` (a ``str``, ``bytes`` or
        ``bytearray`` instance containing a JSON document).
        """
        data = json.loads(s)
        return cls.model_validate(data)

    @classmethod
    def load(cls, path: PathLike) -> Self:
        """
        Load a model instance from ``fp`` (a ``.read()``-supporting
        file-like object containing a JSON document)
        """
        file_path = to_path(path)
        return cls.loads(file_path.read_text())


class SyftMessage(Base):
    version: int = 1
    ulid: ULID = Field(default_factory=ULID)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires: datetime
    sender: str
    url: SyftBoxURL
    headers: dict[str, str]
    body: bytes | None = None

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, value) -> SyftBoxURL:
        if isinstance(value, str):
            return SyftBoxURL(value)
        if isinstance(value, SyftBoxURL):
            return value
        raise ValueError(
            f"Invalid type for url: {type(value)}. Expected str or SyftBoxURL."
        )


class SyftRequest(SyftMessage):
    method: SyftMethod = SyftMethod.GET


class SyftResponse(SyftMessage):
    status_code: SyftStatus = SyftStatus.SYFT_200_OK


class SyftFuture(Base):
    ulid: ULID
    url: SyftBoxURL
    status: SyftStatus = SyftStatus.SYFT_201_CREATED
