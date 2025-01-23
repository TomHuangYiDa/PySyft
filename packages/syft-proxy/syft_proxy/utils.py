import logging


import hashlib
from fastapi.responses import Response
from fastapi.responses import JSONResponse

# from syft_rpc import Request as RPCRequest
from syft_core import SyftBoxURL
from syft_proxy.futures import add_future
from syft_rpc.protocol import SyftResponse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def str_to_bool(bool_str: str | None) -> bool:
    result = False
    bool_str = str(bool_str).lower()
    if bool_str == "true" or bool_str == "1":
        result = True
    return result


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


def syftbox_url_from_params(query_params: dict[str, str]) -> SyftBoxURL:
    datasite = query_params.get("datasite")
    path = query_params.get("path")
    return SyftBoxURL(f"syft://{datasite}{path}")


def syftbox_url_from_full_path(full_path: str) -> SyftBoxURL:
    return SyftBoxURL(f"syft://{full_path}")


def generate_request_key(query_params, body, headers, sender):
    key_data = f"{query_params}|{body}|{headers}|{sender}".encode()
    return hashlib.sha256(key_data).hexdigest()


def create_response(response):
    response_headers = dict(response.headers)
    response_headers["x-forwarded-for"] = response.url.host
    response_headers["x-syft-ulid"] = str(response.ulid)
    return Response(content=response.body, headers=response_headers, status_code=200)


def get_blocking(request):
    block = request.headers.get("x-syft-blocking", None)
    if block is None:
        block = dict(request.query_params).get("block", False)
    return block

def syft_to_json_response(syft_response: SyftResponse) -> JSONResponse:
    """Convert a SyftResponse to FastAPI JSONResponse."""
    response_dict = {
        "version": syft_response.VERSION,
        "ulid": str(syft_response.ulid),  # Convert ULID to string
        "timestamp": syft_response.timestamp.isoformat(),
        "expires": syft_response.expires.isoformat(),
        "sender": syft_response.sender,
        "url": str(syft_response.url),  # Convert SyftBoxURL to string
        "headers": dict(syft_response.headers),
        "status_code": syft_response.status_code.value,  # Get enum value
        "body": syft_response.body.decode() if syft_response.body else None
    }

    # Set HTTP status code based on Syft status
    http_status = 200 if syft_response.is_success else syft_response.status_code.value

    return JSONResponse(
        content=response_dict,
        status_code=http_status,
        headers=dict(syft_response.headers)
    )
