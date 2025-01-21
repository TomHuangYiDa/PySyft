from datetime import datetime, timedelta, timezone

from syft_core.client_shim import Client
from syft_core.url import SyftBoxURL

from .protocol import SyftFuture, SyftMethod, SyftRequest


def send(
    client: Client,
    method: SyftMethod | str,
    url: SyftBoxURL | str,
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
    expiry_secs: int = 10,
) -> SyftFuture:
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

    request_path = client.to_syft_url(file_path)
    future = SyftFuture(request_path=request_path)
    return future


if __name__ == "__main__":
    client = Client.load()
    send(
        client=client,
        method="get",
        url="syft://tauquir@openmined.org/public/rpc/",
        body="ping",
    )
