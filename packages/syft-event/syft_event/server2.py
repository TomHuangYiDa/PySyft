from time import sleep
from syft_core import Client
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileSystemEvent,
    PatternMatchingEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
)
from fnmatch import fnmatch


class FnmatchEventHandler(FileSystemEventHandler):
    def __init__(self, pattern):
        self.pattern = pattern

    def dispatch(self, event: FileSystemEvent) -> None:
        if fnmatch(event.src_path, self.pattern):
            super().dispatch(event)


class RpcRequestHandler(PatternMatchingEventHandler):
    def __init__(self, handler):
        super().__init__(patterns=["**/*.request"], ignore_directories=True)
        self.handler = handler

    def on_any_event(self, event: FileSystemEvent):
        # read the file here itslef
        self.handler(event)


class AnyPatternHandler(FnmatchEventHandler):
    def __init__(self, pattern, handler):
        super().__init__(pattern)
        self.handler = handler

    def on_any_event(self, event: FileSystemEvent):
        self.handler(event)


class SyftEvents:
    def __init__(self, app_name: str, client: Client = None):
        self.app_name = app_name
        self.client = client or Client.load()
        self.app_dir = self.client.api_data(self.app_name)
        self.app_rpc_dir = self.app_dir / "rpc"
        self.obs = Observer()

    def start(self):
        self.app_dir.mkdir(exist_ok=True, parents=True)
        self.app_rpc_dir.mkdir(exist_ok=True, parents=True)
        self.obs.start()

    def run_forever(self):
        self.start()
        while True:
            sleep(1)

    def stop(self):
        self.obs.stop()

    def on_any_request(self, handler_func):
        """Invoke the handler for any request"""

        def wrapper(event):
            return handler_func(event)

        print("Scheduled handler for *")
        self.obs.schedule(
            RpcRequestHandler(wrapper),
            path=self.app_rpc_dir,
            recursive=True,
            event_filter=[FileCreatedEvent],
        )

    def on_request(self, endpoint: str):
        """Invoke the handler for a specific endpoint"""

        if "*" in endpoint or "?" in endpoint:
            raise ValueError("wildcards are not allowed in path")

        # this path must exist so that watch can emit events
        endpoint_path = self.app_rpc_dir / endpoint.lstrip("/").rstrip("/")
        endpoint_path.mkdir(exist_ok=True, parents=True)

        def decorater(func):
            def wrapper(event):
                return func(event)

            self.obs.schedule(
                # use raw path for glob which will be convert to path/*.request
                RpcRequestHandler(wrapper),
                path=endpoint_path,
                recursive=True,
                event_filter=[FileCreatedEvent],
            )
            print("Scheduled handler for", endpoint)
            return wrapper

        return decorater

    def on_file_change(
        self,
        glob_path: str,
        event_filter: list[type[FileSystemEvent]] | None = [FileModifiedEvent],
    ):
        """Invoke the handler if any file changes in the glob path"""

        # substitute the {datasite} with client's datasite in the glob path
        glob_path = glob_path.format(datasite=self.client.email)

        if not glob_path.startswith("**/"):
            glob_path = f"**/{glob_path}"

        def decorater(func):
            def wrapper(event):
                return func(event)

            self.obs.schedule(
                # use raw path for glob which will be convert to path/*.request
                AnyPatternHandler(glob_path, wrapper),
                path=self.client.datasites,
                recursive=True,
                event_filter=event_filter,
            )
            print("Scheduled handler for file change on", glob_path)
            return wrapper

        return decorater


if __name__ == "__main__":
    box = SyftEvents("test_app")

    # requests are always bound to the app
    # root path = {datasite}/api_data/{app_name}/rpc
    @box.on_request("/endpoint")
    def endpoint_request(event):
        print("endpoint", event)

    # requests are always bound to the app
    # root path = {datasite}/api_data/{app_name}/rpc
    @box.on_request("/another")
    def another_request(event):
        print("another", event)

    @box.on_any_request
    def any_request(event):
        print("any", event)

    # root path = ~/SyftBox/datasites/
    # how do i watch for changes on other's datasite?
    @box.on_file_change("{datasite}/**/*.json")
    def on_any_json_file(event):
        print("json file", event)

    print("Running rpc server on", box.app_rpc_dir)
    box.run_forever()
