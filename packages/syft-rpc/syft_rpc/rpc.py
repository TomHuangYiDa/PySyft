from datetime import datetime, timedelta, timezone

from syft_core.client_shim import Client
from syft_core.url import SyftBoxURL

from syft_rpc.protocol import (
    SyftFuture,
    SyftMethod,
    SyftRequest,
    SyftResponse,
    SyftStatus,
)


def send(
    client: Client,
    method: SyftMethod | str,
    url: SyftBoxURL | str,
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
    expiry_secs: int = 10,
) -> SyftFuture:
    """Send an asynchronous request to a Syft Box endpoint and return a future for tracking the response.

    This function creates a SyftRequest, writes it to the local filesystem under the client's workspace,
    and returns a SyftFuture object that can be used to track and retrieve the response.

    Args:
        client: A Syft Client instance used to send the request.
        method: The HTTP method to use. Can be a SyftMethod enum or a string
            (e.g., 'GET', 'POST').
        url: The destination URL. Can be a SyftBoxURL instance or a string in the
            format 'syft://user@domain.com/path'.
        headers: Optional dictionary of HTTP headers to include with the request.
            Defaults to None.
        body: Optional request body. Can be either a string (will be encoded to bytes)
            or raw bytes. Defaults to None.
        expiry_secs: Number of seconds until the request expires. After this time,
            the request will not be processed. Defaults to 10 seconds.

    Returns:
        SyftFuture: A future object that can be used to track and retrieve the response.

    Example:
        >>> client = Client.load()
        >>> future = send(
        ...     client=client,
        ...     method="GET",
        ...     url="syft://data@domain.com/dataset1",
        ...     expiry_secs=30
        ... )
        >>> response = future.result()  # Wait for response
    """
    syft_request = SyftRequest(
        sender=client.email,
        method=method.upper() if isinstance(method, str) else method,
        url=url if isinstance(url, SyftBoxURL) else SyftBoxURL(url),
        headers=headers or {},
        body=body.encode() if isinstance(body, str) else body,
        expires=datetime.now(timezone.utc) + timedelta(seconds=expiry_secs),
    )

    local_path = syft_request.url.to_local_path(client.workspace.datasites)
    file_path = local_path / f"{syft_request.ulid}.request"
    local_path.mkdir(parents=True, exist_ok=True)
    output = syft_request.dump()
    file_path.write_text(output)

    future = SyftFuture(ulid=syft_request.ulid, url=syft_request.url)
    return future


def reply_to(
    request: SyftRequest,
    client: Client,
    body: str | bytes | None = None,
    headers: dict[str, str] | None = None,
    status_code: SyftStatus = SyftStatus.SYFT_200_OK,
    expiry_secs: int = 10,
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
        status_code: HTTP status code for the response. Should be a SyftStatus enum value.
            Defaults to SyftStatus.SYFT_200_OK.
        expiry_secs: Number of seconds until the response expires. After this time,
            the response will be considered stale. Defaults to 10 seconds.

    Returns:
        SyftResponse: The created response object containing all response details.

    Example:
        >>> client = Client(email="service@domain.com")
        >>> # Assuming we have a request
        >>> response = reply_to(
        ...     request=incoming_request,
        ...     client=client,
        ...     body="Request processed successfully",
        ...     status_code=SyftStatus.SYFT_200_OK
        ... )
    """
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
    output = response.dump()
    file_path.write_text(output)

    return response


if __name__ == "__main__":
    client = Client.load()
    future = send(
        client=client,
        method="get",
        url="syft://tauquir@openmined.org/public/rpc/",
        body="ping",
    )
