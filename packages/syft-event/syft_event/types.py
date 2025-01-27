from pydantic import BaseModel, Field
from typing_extensions import Any, Mapping


class Request(BaseModel):
    sender: str
    url: str
    headers: dict = Field(default_factory=dict)
    body: Any = Field(default=None)


class Response(BaseModel):
    content: Any = None
    status_code: int = 200
    headers: Mapping[str, str] | None = None
