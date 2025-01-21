import time
from json import JSONDecodeError
from multiprocessing import Process
from pathlib import Path

from syft_core import Client
from syft_rpc import rpc
from syft_rpc.protocol import SyftRequest

client = Client.load("~/.syftbox/stage/config.json")
APP_NAME = "test_app"
url_path = f"~/SyftBoxStage/datasites/{client.email}/api_data/{APP_NAME}/rpc/"


def process_request(request_path: Path, client: Client):
    try:
        request = SyftRequest.from_path(request_path)
    except JSONDecodeError as e:
        print("Invalid request", e)
        return

    rpc.reply_to(request, client, body="Pong !!!")
    request.unlink(missing_ok=True)


def pong_server(client, url_path):
    url = client.to_syft_url(url_path)
    path = url.to_local_path(datasites_path=client.datasites)

    print("Pong Server is running !!!")

    while True:
        try:
            requests = path.glob("*.request")
            for request_path in requests:
                process_request(request_path, client)
        except FileNotFoundError:
            pass
        except KeyboardInterrupt:
            print("Exiting", flush=True)
            break


def send_ping():
    future = rpc.send(
        client=client,
        method="GET",
        url=client.to_syft_url(url_path),
        headers={"content-type": "application/json"},
        body="Ping !!!",
        expiry_secs=120,
    )
    response = future.wait(timeout=120)
    if future.value:
        print("Received: ", response.decode())
        future.local_path.unlink(missing_ok=True)

    time.sleep(5)


if __name__ == "__main__":
    try:
        process = Process(target=pong_server, args=(client, url_path))
        process.start()

        while True:
            try:
                send_ping()
            except KeyboardInterrupt:
                process.terminate()
                break

    except Exception as e:
        print(e)
