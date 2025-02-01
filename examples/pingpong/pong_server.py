from datetime import UTC, datetime

from loguru import logger
from pydantic import BaseModel
from syft_event import SyftEvents

box = SyftEvents("pingpong")


class PingRequest(BaseModel):
    msg: str
    ts: datetime


class PongResponse(BaseModel):
    msg: str
    ts: datetime


@box.on_request("/ping")
def pong(ping: PingRequest) -> PongResponse:
    logger.info(f"Got ping request - {ping}")
    return PongResponse(msg=f"Pong from {box.client.email}", ts=datetime.now(UTC))


if __name__ == "__main__":
    try:
        print("Running rpc server for", box.app_rpc_dir)
        box.publish_schema()
        box.run_forever()
    except Exception as e:
        print(e)
