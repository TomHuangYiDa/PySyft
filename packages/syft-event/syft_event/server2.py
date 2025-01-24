from pathlib import Path
from time import sleep
from typing import Callable

from syft_core import Client
from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEvent
from watchdog.observers import Observer

from syft_event.handlers import AnyPatternHandler, RpcRequestHandler

DEFAULT_WATCH_EVENTS = [FileCreatedEvent, FileModifiedEvent]


class SyftEvents:
    def __init__(self, app_name: str, client: Client = None):
        self.app_name = app_name
        self.client = client or Client.load()
        self.app_dir = self.client.api_data(self.app_name)
        self.app_rpc_dir = self.app_dir / "rpc"
        self.obs = Observer()
        self.rpc = {}

    def start(self):
        self.app_dir.mkdir(exist_ok=True, parents=True)
        self.app_rpc_dir.mkdir(exist_ok=True, parents=True)
        self.process_pending_requests()
        self.obs.start()

    def process_pending_requests(self):
        # process all pending requests
        for path in self.app_rpc_dir.glob("**/*.request"):
            if path.with_suffix(".response").exists():
                continue
            if path.parent in self.rpc:
                handler = self.rpc[path.parent]
                self.__handle_rpc(path, handler)

    def run_forever(self):
        self.start()
        while True:
            sleep(5)

    def stop(self):
        self.obs.stop()

    def on_request(self, endpoint: str):
        """Bind function to RPC requests at an endpoint"""

        epath = self.__to_endpoint_path(endpoint)

        def decorater(func):
            return self.__register_rpc(epath, func)

        return decorater

    def watch(
        self,
        glob_path: str | list[str],
        event_filter: list[type[FileSystemEvent]] = DEFAULT_WATCH_EVENTS,
    ):
        """Invoke the handler if any file changes in the glob path"""

        if not isinstance(glob_path, list):
            glob_path = [glob_path]

        globs = list(map(self.__format_glob, glob_path))

        def decorater(func):
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

        return decorater

    def __handle_rpc(self, path: Path, func: Callable):
        func(path)
        path.with_suffix(".response").write_text("")

        # try:
        #     req = SyftRequest.load(event.src_path)
        #     resp = handler(req)
        #     # todo check for response types
        # except Exception as e:
        #     print("Error loading request", e)
        pass

    def __register_rpc(self, endpoint: Path, handler: Callable):
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

    def __format_glob(self, path: str):
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
        print("rcp /another: ", req)

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
    box.run_forever()
