import time

from syft_core import Client
from syft_rpc import rpc
from syft_rpc.protocol import SyftFuture

client = Client.load("~/.syftbox/stage/config.json")
url_path = "~/SyftBoxStage/datasites/khoa@openmined.org/public/rpc"
syft_url = client.to_syft_url(url_path)
print(f"sending syft_url: {syft_url}")
future: SyftFuture = rpc.send(
    client=client,
    method="GET",
    url=client.to_syft_url(url_path),
    headers={"content-type": "application/json"},
    body="Ping !!!",
    expiry_secs=120,
)

# wait for response
# path_to_file = future.url.to_local_path(client.workspace.datasites)
# response_file = path_to_file / f"{future.ulid}.response"
# while True:
#     if response_file.exists():
#         print("Response received at: ", time.time())
#         break

import pdb; pdb.set_trace()