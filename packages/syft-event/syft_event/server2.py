import json
from pathlib import Path
from threading import Event
from typing import Callable

from pydantic import BaseModel
from syft_core import Client
from syft_rpc import rpc
from syft_rpc.protocol import SyftRequest
from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEvent
from watchdog.observers import Observer

from syft_event.handlers import AnyPatternHandler, RpcRequestHandler
from syft_event.schema import generate_schema
from syft_event.types import Request

DEFAULT_WATCH_EVENTS = [FileCreatedEvent, FileModifiedEvent]


class SyftEvents:
    def __init__(self, app_name: str, client: Client = None):
        self.app_name = app_name
        self.client = client or Client.load()
        self.app_dir = self.client.api_data(self.app_name)
        self.app_rpc_dir = self.app_dir / "rpc"
        self.obs = Observer()
        self.rpc: dict[Path, Callable] = {}
        self._stop_event = Event()

    def start(self) -> None:
        self.app_dir.mkdir(exist_ok=True, parents=True)
        self.app_rpc_dir.mkdir(exist_ok=True, parents=True)
        try:
            self.process_pending_requests()
        except Exception as e:
            print("Error processing pending requests", e)
        self.obs.start()

    def publish_schema(self) -> None:
        schema = {}
        for endpoint, handler in self.rpc.items():
            handler = generate_schema(handler)
            ep_name = endpoint.relative_to(self.app_rpc_dir)
            ep_name = "/" + str(ep_name).replace("\\", "/")
            schema[ep_name] = handler

        schema_path = self.app_rpc_dir / "rpc.schema.json"
        schema_path.write_text(json.dumps(schema, indent=2))

    def process_pending_requests(self) -> None:
        # process all pending requests
        for path in self.app_rpc_dir.glob("**/*.request"):
            if path.with_suffix(".response").exists():
                continue
            if path.parent in self.rpc:
                handler = self.rpc[path.parent]
                self.__handle_rpc(path, handler)

    def run_forever(self) -> None:
        self.start()
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        self._stop_event.set()
        self.obs.stop()
        self.obs.join()

    def on_request(self, endpoint: str) -> Callable:
        """Bind function to RPC requests at an endpoint"""

        def decorator(func):
            epath = self.__to_endpoint_path(endpoint)
            self.__register_rpc(epath, func)
            return func

        return decorator

    def watch(
        self,
        glob_path: str | list[str],
        event_filter: list[type[FileSystemEvent]] = DEFAULT_WATCH_EVENTS,
    ):
        """Invoke the handler if any file changes in the glob path"""

        if not isinstance(glob_path, list):
            glob_path = [glob_path]

        globs = [self.__format_glob(path) for path in glob_path]

        def decorator(func):
            def wrapper(event):
                return func(event)

            self.obs.schedule(
                # use raw path for glob which will be convert to path/*.request
                AnyPatternHandler(globs, wrapper),
                path=self.client.datasites,
                recursive=True,
                event_filter=event_filter,
            )
            return wrapper

        return decorator

    def __handle_rpc(self, path: Path, func: Callable):
        try:
            req = SyftRequest.load(path)
            # todo! what do we do here?
            if req.is_expired:
                return
            evt_req = Request(
                sender=req.sender,
                url=req.url,
                headers=req.headers,
                body=req.body,
            )
            resp = func(evt_req)
            if resp is None:
                data = ""
                content_type = "text/plain"
            elif isinstance(resp, (dict, BaseModel)):
                data = json.dumps(resp)
                content_type = "application/json"
            else:
                data = resp
                content_type = "application/octet-stream"
            rpc.reply_to(
                req,
                body=data,
                headers={"Content-Type": content_type},
                client=self.client,
            )
        except Exception as e:
            print("Error loading request", e)

    def __register_rpc(self, endpoint: Path, handler: Callable) -> Callable:
        def on_rpc_request(event: FileSystemEvent):
            return self.__handle_rpc(Path(event.src_path), handler)

        self.obs.schedule(
            RpcRequestHandler(on_rpc_request),
            path=endpoint,
            recursive=True,
            event_filter=[FileCreatedEvent],
        )
        self.rpc[endpoint] = handler
        return on_rpc_request

    def __to_endpoint_path(self, endpoint: str) -> Path:
        if "*" in endpoint or "?" in endpoint:
            raise ValueError("wildcards are not allowed in path")

        # this path must exist so that watch can emit events
        epath = self.app_rpc_dir / endpoint.lstrip("/").rstrip("/")
        epath.mkdir(exist_ok=True, parents=True)
        return epath

    def __format_glob(self, path: str) -> str:
        # replace placeholders with actual values
        path = path.format(
            email=self.client.email,
            datasite=self.client.email,
            api_data=self.client.api_data(self.app_name),
        )
        if not path.startswith("**/"):
            path = f"**/{path}"
        return path


if __name__ == "__main__":
    box = SyftEvents("test_app")

    # requests are always bound to the app
    # root path = {datasite}/api_data/{app_name}/rpc
    @box.on_request("/endpoint")
    def endpoint_request(req):
        print("rpc /endpoint:", req)

    # requests are always bound to the app
    # root path = {datasite}/api_data/{app_name}/rpc
    @box.on_request("/another")
    def another_request(req):
        print("rpc /another: ", req)

    # root path = ~/SyftBox/datasites/
    @box.watch("{datasite}/**/*.json")
    def all_json_on_my_datasite(event):
        print("watch {datasite}/**/*.json:".format(datasite=box.client.email), event)

    # root path = ~/SyftBox/datasites/
    @box.watch("test@openined.org/*.json")
    def jsons_in_some_datasite(event):
        print("watch test@openined.org/*.json:", event)

    # root path = ~/SyftBox/datasites/
    @box.watch("**/*.json")
    def all_jsons_everywhere(event):
        print("watch **/*.json:", event)

    print("Running rpc server for", box.app_rpc_dir)
    box.publish_schema()
    box.run_forever()


# if __name__ == "__main__":
#     box = SyftEvents("vector_store")

#     # requests are always bound to the app
#     # root path = {datasite}/api_data/{app_name}/rpc
#     @box.on_request("/doc_query")
#     def query(query: str) -> list[str]:
#         """Return similar documents for a given query"""
#         return []

#     @box.on_request("/doc_similarity")
#     def query_embedding(embedding: np.array) -> np.array:
#         """Return similar documents for a given embedding"""
#         return []

#     print("Running rpc server for", box.app_rpc_dir)
#     box.publish_schema()
#     box.run_forever()
