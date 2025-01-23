from time import sleep

from syft_core import Client
from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEvent
from watchdog.observers import Observer

from .handlers import AnyPatternHandler, RpcRequestHandler


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
            return wrapper

        return decorater

    def on_file_change(
        self,
        glob_path: str | list[str],
        event_filter: list[type[FileSystemEvent]] | None = [FileModifiedEvent],
    ):
        """Invoke the handler if any file changes in the glob path"""

        if not isinstance(glob_path, list):
            glob_path = [glob_path]

        def format_globs(path: str):
            # replace placeholders with actual values
            path = path.format(
                datasite=self.client.email,
                api_data=self.client.api_data(self.app_name),
            )
            if not path.startswith("**/"):
                path = f"**/{path}"
            return path

        globs = list(map(format_globs, glob_path))

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
    @box.on_file_change("{datasite}/**/*.json")
    def all_json_on_my_datasite(event):
        print("json file", event)

    # root path = ~/SyftBox/datasites/
    @box.on_file_change("test@openined.org/*.json")
    def all_jsons_in_some_datasite(event):
        print("json file", event)

    # root path = ~/SyftBox/datasites/
    @box.on_file_change("**/*.json")
    def all_jsons_everywhere(event):
        print("json file", event)

    print("Running rpc server on", box.app_rpc_dir)
    box.run_forever()
