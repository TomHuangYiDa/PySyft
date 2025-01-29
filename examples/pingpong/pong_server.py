from syft_event import SyftEvents
from syft_event.types import Request

box = SyftEvents("pingpong")


@box.on_request("/ping")
def pong(req: Request) -> str:
    print(f"Got ping request {req.id} - {req.sender} - {req.body}")
    return "PONG !!!"


if __name__ == "__main__":
    try:
        print("Running rpc server for", box.app_rpc_dir)
        box.publish_schema()
        box.run_forever()
    except Exception as e:
        print(e)
