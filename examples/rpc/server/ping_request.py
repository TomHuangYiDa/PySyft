import time

from syft_core import Client
from syft_rpc import rpc

client = Client.load("~/.syftbox/stage/config.json")
url_path = "~/SyftBoxStage/datasites/shubham@openmined.org/public/rpc"


def send_ping():
    start = time.time()
    future = rpc.send(
        client=client,
        method="GET",
        url=client.to_syft_url(url_path),
        headers={"content-type": "application/json"},
        body="Ping !!!",
        expiry_secs=120,
    )
    response = future.wait(timeout=300)
    print(response.body.decode())
    end = time.time()
    print("Time taken: ", end - start)


if __name__ == "__main__":
    send_ping()
