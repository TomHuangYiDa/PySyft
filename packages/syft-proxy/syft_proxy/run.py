import hashlib
import logging
from fastapi import HTTPException
import time
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from syft_rpc import Request as RPCRequest, SyftBoxURL
from syft_core import Client
from contextlib import asynccontextmanager
import asyncio
from asyncio import Future

from utils import (
    create_response,
    generate_request_key,
    get_blocking,
    make_request,
    syftbox_url_from_params,
    syftbox_url_from_full_path
)

from futures import add_future, clean_expired_futures, futures, FUTURE_EXPIRATION_SECONDS

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

client_config = Client.load()

app = FastAPI()


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


@app.post("/ask", include_in_schema=False)
async def ask(request: Request) -> JSONResponse:
    body = await request.json()
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    client_ip = request.client.host
    # we need to forward the message to the LLM and get back the Future?
    result = {
        "response": f"Got the message: {body['content']} from IP: {client_ip}",
        "files": [
            {
                "name": "nuclear_weapons.pdf",
                "size": "12,458 KB",
                "modified": "2024-01-15 14:23:45",
                "type": "PDF"
            },
            {
                "name": "national_secrets.xlsx",
                "size": "8,234 KB",
                "modified": "2024-01-10 09:15:30",
                "type": "XLSX"
            },
    ]}
    return JSONResponse(result)


@app.post("/rpc", response_class=JSONResponse, include_in_schema=False)
async def rpc(request: Request):
    sender = request.client.host
    body = await request.body()
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    print("query_params", query_params)

    timeout = 60
    if "timeout" in query_params:
        timeout = float(query_params["timeout"])

    # Generate a unique key for the request
    request_key = generate_request_key(query_params, body, headers, sender)
    blocking = get_blocking(request)
    logger.info(f"INCOMING REQUEST blocking {blocking}: {request_key}")

    # Check if this key exists in the futures dict
    if request_key in futures:
        logger.info(f"Getting stored future: {request_key}")
        stored_future = futures[request_key]["future"]  # Access future from the dict
        try:
            response = stored_future.wait(timeout=timeout - 1.1)
            del futures[request_key]  # Cleanup once resolved
            return create_response(response)
        except TimeoutError:
            logger.info(f"Timeout for stored future: {request_key}")
            return Response(
                content=b"",
                headers={"Retry-After": "1", "X-Request-Key": request_key},
                status_code=504,
            )

    # Handle new request
    response = make_request(
        query_params, body, headers, sender, blocking, timeout, request_key
    )
    return response


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


# accepts normal HTTP
@app.get("/rpc/{full_path:path}")
async def rpc(full_path: str, request: Request):
    sender = request.client.host
    body = await request.body()
    headers = dict(request.headers)
    query_params = dict(request.query_params)

    # turns into SyftBox RPC message
    headers["x-forwarded-for"] = sender
    headers["x-forwarded-proto"] = "http"
    # rpc = RPCRequest()
    syftbox_url = syftbox_url_from_full_path(full_path)
    print(">>> syftbox_url_from_full_path", syftbox_url)
    
    # calls .get
    # future_response = rpc.send(syftbox_url, body=body, headers=headers, method="get")
    
    # returns future
    # return future_response.wait(timeout=timeout - 1.1)
    return "SyftFuture is waiting for you!"


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
