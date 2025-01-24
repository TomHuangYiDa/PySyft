from pathlib import Path
from time import sleep

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

    def on_any_request(self, func):
        """Invoke the handler for any request"""

        def wrapper(event):
            return func(event)

        self.obs.schedule(
            RpcRequestHandler(wrapper),
            path=self.app_rpc_dir,
            recursive=True,
            event_filter=[FileCreatedEvent],
        )

    def on_request(self, endpoint: str):
        """Handle requests at `{api_data}/rpc/{endpoint}`"""

        epath = self.__to_endpoint_path(endpoint)

        def decorater(func):
            def wrapper(event):
                return func(event)

            self.obs.schedule(
                # use raw path for glob which will be convert to path/*.request
                RpcRequestHandler(wrapper),
                path=epath,
                recursive=True,
                event_filter=[FileCreatedEvent],
            )
            return wrapper

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
    def endpoint_request(event):
        print("endpoint", event)

    # requests are always bound to the app
    # root path = {datasite}/api_data/{app_name}/rpc
    @box.on_request("/another")
    def another_request(event):
        print("another", event)

    # Any request on any endpoint
    @box.on_any_request
    def any_request(event):
        print("any", event)

    # root path = ~/SyftBox/datasites/
    @box.watch("{datasite}/**/*.json")
    def all_json_on_my_datasite(event):
        print("{datasite} json file".format(datasite=box.client.email), event)

    # root path = ~/SyftBox/datasites/
    @box.watch("test@openined.org/*.json")
    def jsons_in_some_datasite(event):
        print("test@openmined,org json file", event)

    # root path = ~/SyftBox/datasites/
    @box.watch("**/*.json")
    def all_jsons_everywhere(event):
        print("all json file", event)

    print("Running rpc server on", box.app_rpc_dir)
    box.run_forever()
