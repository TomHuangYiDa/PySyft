import hashlib
import logging
import time
from pathlib import Path
import uvicorn
from fastapi import HTTPException
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
import asyncio
from asyncio import Future
from ulid import ULID

from syft_core.url import SyftBoxURL
from syft_core import Client
from syft_rpc.protocol import SyftFuture, SyftTimeoutError, SyftResponse, SyftRequest
from syft_rpc import rpc
from syft_proxy.utils import (
    create_response,
    generate_request_key,
    get_blocking,
    make_request,
    syftbox_url_from_params,
    syftbox_url_from_full_path,
    syft_to_json_response,
)

from syft_proxy.futures import (
    add_future, 
    clean_expired_futures, 
    futures, 
    FUTURE_EXPIRATION_SECONDS
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# client_config = Client.load()

app = FastAPI()
client = Client.load("~/.syftbox/stage/config.json")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to manage startup and shutdown tasks."""

    async def cleanup_task():
        while True:
            clean_expired_futures()
            await asyncio.sleep(
                FUTURE_EXPIRATION_SECONDS // 2
            )  # Clean up every 30 seconds

    cleanup_task_handle = asyncio.create_task(cleanup_task())
    try:
        yield  # Startup logic here if needed
    finally:
        cleanup_task_handle.cancel()
        try:
            await cleanup_task_handle
        except asyncio.CancelledError:
            pass  # Suppress cancellation error during shutdown


app = FastAPI(lifespan=lifespan)


@app.post("/chat", include_in_schema=False)
async def chat(request: Request) -> JSONResponse:
    body = await request.json()
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    client_ip = request.client.host
    # we need to forward the message to the LLM and get back the Future?
    result = {
        "response": f"Got the message: {body['content']} from IP: {client_ip}. Will forward to LLM.",
        "headers": headers,
        "query_params": query_params,
    }
    return JSONResponse(result)


@app.post("/rpc/reply/{request_id}", response_class=JSONResponse, include_in_schema=False)
async def rpc_reply(request_id: str, request: Request):
    sending_host = request.client.host
    print(f"Received request from {sending_host}")
    body = await request.body()
    headers = dict(request.headers)
    query_params = dict(request.query_params)

    timeout = 1
    if "timeout" in query_params:
        timeout = float(query_params["timeout"])
        
    rpc_url: SyftBoxURL = syftbox_url_from_params(query_params)
    path: Path = rpc_url.to_local_path(datasites_path=client.datasites)
    import pdb; pdb.set_trace()
    # request_path: Path = 
    # request = SyftRequest.load(request_path)
    # response: SyftResponse = rpc.reply_to(request, client, body="Pong !!!")


@app.post("/rpc", response_class=JSONResponse, include_in_schema=False)
async def rpc_send(request: Request):
    sending_host = request.client.host
    print(f"Received request from {sending_host}")
    body = await request.body()
    headers = dict(request.headers)
    query_params = dict(request.query_params)

    timeout = 1
    if "timeout" in query_params:
        timeout = float(query_params["timeout"])

    rpc_url: SyftBoxURL = syftbox_url_from_params(query_params)
    future: SyftFuture = rpc.send(
        client=client,
        method=query_params.get("method", "GET"),
        url=rpc_url,
        headers=headers,
        body=body,
        expiry_secs=120,
    )
    blocking = get_blocking(request)
    if blocking:
        try:
            # This will block until response is received or timeout occurs
            response: SyftResponse = future.wait(timeout=timeout)
            json_response: JSONResponse = syft_to_json_response(response)
            return json_response 
        except SyftTimeoutError as e:
            logger.error(f"Timeout: {e}")
            return JSONResponse(
                {"status": "timeout", "message": str(e)}, 
                status_code=408
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            return JSONResponse(
                {"status": "error", "message": str(e)},
                status_code=500
            )
    else:
        return JSONResponse({
            "status": "pending",
            "future_id": str(future.ulid),
            "poll_url": f"/rpc/status/{future.ulid}"
        })


@app.get(
    "/rpc/status/{request_key}", response_class=JSONResponse, include_in_schema=False
)
async def rpc_status(request_key: str, request: Request):
    logger.info(f"Checking status for request key: {request_key}")
    future1 = Future()
    future1.set_result({
        "status": "success",
        "data": {
            "user_id": 123,
            "message": "Data processing complete",
            "results": [1, 2, 3]
        }
    })
    add_future(request_key, future1)

    timeout = float(
        request.query_params.get("timeout", 60)
    )  # Optional timeout override

    if request_key not in futures:
        logger.info(f"Request key {request_key} not found.")
        raise HTTPException(
            status_code=404, detail=f"Request key {request_key} not found."
        )

    future_response = futures[request_key]["future"]
    try:
        # response = future_response.wait(timeout=timeout - 1.1)
        # del futures[request_key]  # Cleanup once resolved
        # return create_response(response)
        response = await asyncio.wait_for(future_response, timeout=3)
        del futures[request_key]  # Cleanup once resolved
        return response
    except TimeoutError:
        logger.info(f"Timeout for stored future: {request_key}")
        return Response(
            content=b"",
            headers={"Retry-After": "1", "X-Request-Key": request_key},
            status_code=504,
        )


@app.get(
    "/rpc/list", response_class=JSONResponse, include_in_schema=False
)
async def rpc_list(request: Request):
    futures = []
    return JSONResponse(futures)


def main() -> None:
    debug = True
    uvicorn.run(
        "run:app" if debug else app,
        host="0.0.0.0",
        port=9081,
        log_level="debug" if debug else "info",
        reload=debug,
        reload_dirs="./",
    )


if __name__ == "__main__":
    main()
