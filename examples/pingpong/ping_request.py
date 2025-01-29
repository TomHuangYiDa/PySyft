import time

from syft_core import Client
from syft_rpc import rpc


def send_ping():
    start = time.time()
    client = Client.load()
    future = rpc.send(
        url=f"syft://{client.email}/api_data/pingpong/rpc/ping",
        body="Ping !!!",
        expiry="5m",
        cache=True,
    )
    print(f"Request {future.id} sent to {future.request.url}")
    response = future.wait(timeout=300)
    print("Response: ", response.status_code, response.body, response.headers)
    end = time.time()
    print("Time taken: ", end - start)


if __name__ == "__main__":
    send_ping()
