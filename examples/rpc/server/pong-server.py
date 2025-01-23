import datetime
from json import JSONDecodeError
from pathlib import Path

from syft_core import Client
from syft_rpc import rpc
from syft_rpc.protocol import SyftRequest

client = Client.load("~/.syftbox/stage/config.json")
url_path = "~/SyftBoxStage/datasites/tauquir@openmined.org/public/rpc"


def process_request(request_path: Path, client: Client):
    try:
        request = SyftRequest.load(request_path)

    except JSONDecodeError as e:
        print("Invalid request", e)
        return
    timedelta = datetime.datetime.now(datetime.UTC) - request.timestamp
    print(f"Request received at: {timedelta} ", request.body)
    rpc.reply_to(request, client, body="Pong !!!")
    request_path.unlink()


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


if __name__ == "__main__":
    try:
        pong_server(client, url_path)
    except Exception as e:
        print(e)
