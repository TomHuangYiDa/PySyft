import time

from syft_core import Client
from syft_rpc import rpc

client = Client.load("~/.syftbox/stage/config.json")
url_path = "~/SyftBoxStage/datasites/tauquir@openmined.org/public/rpc"


def wait_for_response(future, client):
    path_to_file = future.url.to_local_path(client.workspace.datasites)
    response_file = path_to_file / f"{future.ulid}.response"
    while True:
        if response_file.exists():
            print("Response received at: ", time.time())
            break


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
    wait_for_response(future, client)
    end = time.time()
    print("Time taken: ", end - start)


if __name__ == "__main__":
    send_ping()
