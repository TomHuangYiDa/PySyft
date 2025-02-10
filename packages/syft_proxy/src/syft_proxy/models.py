from enum import Enum

from pydantic import BaseModel, Field
from syft_rpc import SyftRequest, SyftResponse
from syft_rpc.rpc import DEFAULT_EXPIRY
from typing_extensions import Any, List, Optional, Union


class RPCRequestBase(BaseModel):
    body: Any
    headers: dict[str, str] = Field(default_factory=dict)
    expiry: str = Field(default=DEFAULT_EXPIRY)
    cache: bool = Field(default=False)


class RPCSendRequest(RPCRequestBase):
    app_name: str = Field(..., min_length=3)
    url: str


class RPCBroadcastRequest(RPCRequestBase):
    urls: List[str]


class RPCBroadcastResult(BaseModel):
    id: str
    requests: List[SyftRequest]


class RPCStatusCode(Enum):
    NOT_FOUND = "RPC_NOT_FOUND"
    PENDING = "RPC_PENDING"
    COMPLETED = "RPC_COMPLETED"
    ERROR = "RPC_ERROR"


class RPCStatus(BaseModel):
    id: str
    status: RPCStatusCode
    request: Optional[Union[SyftRequest, List[SyftRequest]]]
    response: Optional[Union[SyftResponse, List[SyftResponse]]]
