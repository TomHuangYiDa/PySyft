import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from loguru import logger
from pydantic import BaseModel
from syft_core import Client
from syft_rpc import rpc


@dataclass
class PingRequest:
    msg: str
    ts: datetime = field(default_factory=lambda: datetime.now(UTC).isoformat())


class PongResponse(BaseModel):
    msg: str
    ts: datetime


def send_ping():
    client = Client.load()
    msg_bytes = json.dumps(asdict(PingRequest(msg="hello!")))

    start = time.time()
    future = rpc.send(
        url=f"syft://{client.email}/api_data/pingpong/rpc/ping",
        body=msg_bytes,
        expiry="5m",
        cache=True,
    )
    logger.debug(f"Request: {future.request}")

    try:
        response = future.wait(timeout=300)
        response.raise_for_status()
        response = PongResponse.model_validate_json(response.body)
        logger.info(f"Response: {response}. Time taken: {time.time() - start}")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    send_ping()
