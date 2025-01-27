from datetime import datetime, timedelta, timezone

from syft_core.client_shim import Client
from syft_core.url import SyftBoxURL

from syft_rpc.protocol import (
    SyftBulkFuture,
    SyftError,
    SyftFuture,
    SyftMethod,
    SyftRequest,
    SyftResponse,
    SyftStatus,
)


def send(
    method: SyftMethod | str,
    url: SyftBoxURL | str,
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
    client: Client | None = None,
    expiry_secs: int = 10,
    no_cache: bool = False,
) -> SyftFuture:
    """Send an asynchronous request to a Syft Box endpoint and return a future for tracking the response.

    This function creates a SyftRequest, writes it to the local filesystem under the client's workspace,
    and returns a SyftFuture object that can be used to track and retrieve the response.

    Args:
        method: The HTTP method to use. Can be a SyftMethod enum or a string
            (e.g., 'GET', 'POST').
        url: The destination URL. Can be a SyftBoxURL instance or a string in the
            format 'syft://user@domain.com/path'.
        headers: Optional dictionary of HTTP headers to include with the request.
            Defaults to None.
        body: Optional request body. Can be either a string (will be encoded to bytes)
            or raw bytes. Defaults to None.
        client: A Syft Client instance used to send the request. If not provided,
            the default client will be loaded.
        expiry_secs: Number of seconds until the request expires. After this time,
            the request will not be processed. Defaults to 10 seconds.
        no_cache: If True, ignore any cached future and make a fresh request.

    Returns:
        SyftFuture: A future object that can be used to track and retrieve the response.

    Example:
        >>> future = send(
        ...     method="GET",
        ...     url="syft://data@domain.com/dataset1",
        ...     expiry_secs=30
        ... )
        >>> response = future.result()  # Wait for response
    """

    # If client is not provided, load the default client
    client = Client.load() if client is None else client

    syft_request = SyftRequest(
        sender=client.email,
        method=method.upper() if isinstance(method, str) else method,
        url=url if isinstance(url, SyftBoxURL) else SyftBoxURL(url),
        headers=headers or {},
        body=body.encode() if isinstance(body, str) else body,
        expires=datetime.now(timezone.utc) + timedelta(seconds=expiry_secs),
    )
    local_path = syft_request.url.to_local_path(client.workspace.datasites)

    message_hash = syft_request.get_message_hash()
    state_path = local_path / f".{message_hash}.state"

    # Check if we already have a cached future that hasn't expired
    if not no_cache and state_path.exists():
        future = SyftFuture.load(state_path)
        if not future.is_expired:
            return future

    # We need to make a fresh request and persist the future to a state
    file_path = local_path / f"{syft_request.ulid}.request"
    try:
        local_path.mkdir(parents=True, exist_ok=True)
        syft_request.dump(file_path)
    except Exception as e:
        raise SyftError(f"Failed to write request to {file_path}: {e}")

    future = SyftFuture(
        ulid=syft_request.ulid,
        url=syft_request.url,
        local_path=local_path,
        expires=syft_request.expires,
    )
    future.dump(state_path)
    return future


def broadcast(
    method: SyftMethod | str,
    urls: list[SyftBoxURL | str],
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
    expiry_secs: int = 10,
    no_cache: bool = False,
    client: Client | None = None,
) -> SyftBulkFuture:
    """Broadcast an asynchronous request to multiple Syft Box endpoints and return a bulk future.

    This function creates a SyftRequest for each URL in the list,
    writes them to the local filesystem under the client's workspace, and
    returns a SyftBulkFuture object that can be used to track and retrieve multiple responses.

    Args:
        method: The HTTP method to use. Can be a SyftMethod enum or a string
            (e.g., 'GET', 'POST').
        urls: List of destination URLs. Each can be a SyftBoxURL instance or a string in
            the format 'syft://user@domain.com/path'.
        headers: Optional dictionary of HTTP headers to include with the requests.
            Defaults to None.
        body: Optional request body. Can be either a string (will be encoded to bytes)
            or raw bytes. Defaults to None.
        client: A Syft Client instance used to send the requests. If not provided,
            the default client will be loaded.
        expiry_secs: Number of seconds until the requests expire. After this time,
            requests will not be processed. Defaults to 10 seconds.
        no_cache: If True, ignore any cached futures and make fresh requests.

    Returns:
        SyftBulkFuture: A bulk future object that can be used to track and retrieve multiple responses.

    Example:
        >>> future = broadcast(
        ...     method="GET",
        ...     urls=["syft://user1@domain.com/public/rpc/", "syft://user2@domain.com/public/rpc/"],
        ...     expiry_secs=300,
        ... )
        >>> responses = future.gather_completed()  # Wait for all responses
    """

    # If client is not provided, load the default client
    client = Client.load() if client is None else client

    bulk_future = SyftBulkFuture(
        futures=[
            send(
                method=method,
                url=url,
                headers=headers,
                body=body,
                client=client,
                expiry_secs=expiry_secs,
                no_cache=no_cache,
            )
            for url in urls
        ]
    )
    return bulk_future


def reply_to(
    request: SyftRequest,
    body: str | bytes | None = None,
    headers: dict[str, str] | None = None,
    status_code: SyftStatus = SyftStatus.SYFT_200_OK,
    expiry_secs: int = 10,
    client: Client | None = None,
) -> SyftResponse:
    """Create and store a response to a Syft request.

    This function creates a SyftResponse object corresponding to a given SyftRequest,
    writes it to the local filesystem in the client's workspace, and returns the response object.

    Args:
        request: The original SyftRequest to respond to.
        client: A Syft Client instance used to send the response.
        body: Optional response body. Can be either a string (will be encoded to bytes)
            or raw bytes. Defaults to None.
        headers: Optional dictionary of HTTP headers to include with the response.
            Defaults to None.
        client: A Syft Client instance used to send the response. If not provided,
            the default client will be loaded.
        status_code: HTTP status code for the response. Should be a SyftStatus enum value.
            Defaults to SyftStatus.SYFT_200_OK.
        expiry_secs: Number of seconds until the response expires. After this time,
            the response will be considered stale. Defaults to 10 seconds.

    Returns:
        SyftResponse: The created response object containing all response details.

    Example:
        >>> # Assuming we have a request
        >>> response = reply_to(
        ...     request=incoming_request,
        ...     body="Request processed successfully",
        ...     status_code=SyftStatus.SYFT_200_OK
        ... )
    """

    # If client is not provided, load the default client
    client = Client.load() if client is None else client

    response = SyftResponse(
        ulid=request.ulid,
        sender=client.email,
        method=request.method,
        url=request.url,
        headers=headers or {},
        body=body.encode() if isinstance(body, str) else body,
        expires=datetime.now(timezone.utc) + timedelta(seconds=expiry_secs),
        status_code=status_code,
    )

    local_path = response.url.to_local_path(client.workspace.datasites)
    file_path = local_path / f"{response.ulid}.response"
    local_path.mkdir(parents=True, exist_ok=True)
    response.dump(file_path)

    return response


if __name__ == "__main__":
    client = Client.load()
    future = send(
        client=client,
        method="get",
        url="syft://tauquir@openmined.org/public/rpc/",
        body="ping",
    )
    print(future)
