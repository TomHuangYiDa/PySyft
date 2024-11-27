import hashlib
import logging
from fastapi import HTTPException
import time
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from syft_rpc import Request as RPCRequest, SyftBoxURL
from syftbox.lib import Client
from contextlib import asynccontextmanager
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

client_config = Client.load()

app = FastAPI()

# Futures dictionary to store futures and their timestamps
futures = {}

# Expiration time in seconds (configurable)
FUTURE_EXPIRATION_SECONDS = 60


def add_future(request_key, future_response):
    """Add a future to the futures dict with a timestamp."""
    futures[request_key] = {"future": future_response, "timestamp": time.time()}


def clean_expired_futures():
    """Remove expired futures from the dictionary."""
    current_time = time.time()
    expired_keys = [
        key
        for key, value in futures.items()
        if current_time - value["timestamp"] > FUTURE_EXPIRATION_SECONDS
    ]
    for key in expired_keys:
        logger.info(f"Removing expired future: {key}")
        del futures[key]


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


def str_to_bool(bool_str: str | None) -> bool:
    result = False
    bool_str = str(bool_str).lower()
    if bool_str == "true" or bool_str == "1":
        result = True
    return result


def get_blocking(request):
    block = request.headers.get("x-syft-blocking", None)
    print("1 block", block)
    if block is None:
        block = dict(request.query_params).get("block", True)  # default to on
        print("2 block", block)
    result = str_to_bool(block)
    print("3 block", result)
    return result


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
        response = future_response.wait(timeout=timeout - 1.1)
        del futures[request_key]  # Cleanup once resolved
        return create_response(response)
    except TimeoutError:
        logger.info(f"Timeout for stored future: {request_key}")
        return Response(
            content=b"",
            headers={"Retry-After": "1", "X-Request-Key": request_key},
            status_code=504,
        )


def make_request(query_params, body, headers, sender, blocking, timeout, request_key):
    headers["x-forwarded-for"] = sender
    headers["x-forwarded-proto"] = "http"
    rpc = RPCRequest()
    syftbox_url = syftbox_url_from_params(query_params)

    try:
        future_response = rpc.get(syftbox_url, body=body, headers=headers)

        if blocking:
            try:
                logger.info(
                    f"Making blocking request with timeout {timeout-1.1}: {request_key}"
                )
                response = future_response.wait(timeout=timeout - 1.1)
                return create_response(response)
            except TimeoutError:
                add_future(request_key, future_response)  # Add future with timestamp
                logger.info(f"Timeout, storing future: {request_key}")
                return Response(
                    content=b"",
                    headers={
                        "Retry-After": "1",
                        "X-Request-Key": request_key,
                        "Location": f"/rpc/status/{request_key}",
                    },
                    status_code=504,
                )
        else:
            add_future(request_key, future_response)  # Add future with timestamp
            logger.info(f"Non-blocking request, storing future: {request_key}")
            return Response(
                content=b"Future stored",
                headers={
                    "X-Request-Key": request_key,
                    "Location": f"/rpc/status/{request_key}",
                },
                status_code=202,
            )

    except Exception as e:
        logger.info(f"Exception occurred: {e}", exc_info=True)
        return Response(content=b"Internal server error", status_code=500)


def syftbox_url_from_params(query_params: dict[str, str]) -> str:
    datasite = query_params.get("datasite")
    path = query_params.get("path")
    return SyftBoxURL(f"syft://{datasite}{path}")


def generate_request_key(query_params, body, headers, sender):
    key_data = f"{query_params}|{body}|{headers}|{sender}".encode()
    return hashlib.sha256(key_data).hexdigest()


def create_response(response):
    response_headers = dict(response.headers)
    response_headers["x-forwarded-for"] = response.url.host
    response_headers["x-syft-ulid"] = str(response.ulid)
    return Response(content=response.body, headers=response_headers, status_code=200)


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
