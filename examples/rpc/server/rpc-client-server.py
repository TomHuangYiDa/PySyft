import json
import time
from datetime import datetime, timezone
from multiprocessing import Process
from pathlib import Path

from syft_core import Client
from syft_rpc.rpc import Request, RequestMessage

client = Client.load("~/.syftbox/stage/config.json")
APP_NAME = "test_app"
url_path = f"~/SyftBoxStage/datasites/{client.email}/api_data/{APP_NAME}/rpc/"


def process_request(request: Path, client: Client):
    with open(request, "rb") as f:
        request_data = f.read()

        if not request_data:
            return

        msg = RequestMessage.load(request_data)

        response_msg = msg.reply(
            from_sender=client.email,
            body=json.dumps(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": "Pong !!!",
                }
            ),
            status_code=200,
            headers={"content-type": "application/json"},
        )
        response_msg.send(client=client)
        request.unlink(missing_ok=True)


def pong_server(client, url_path):
    url = client.to_syft_url(url_path)
    path = url.to_local_path(datasites_path=client.datasites)

    print("Pong Server is running !!!")

    while True:
        try:
            requests = path.glob("*.request")
            for request in requests:
                process_request(request, client)
        except FileNotFoundError:
            pass
        except KeyboardInterrupt:
            print("Exiting", flush=True)
            break


def send_ping():
    requests = Request(client=client)
    url = client.to_syft_url(url_path)
    data = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": "Ping !!!"}
    print(f"Sending: {data}")
    future = requests.get(
        url=url,
        headers={"content-type": "application/json"},
        body=json.dumps(data),
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
