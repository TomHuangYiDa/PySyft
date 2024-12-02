import asyncio
import os
import time
from collections.abc import Callable
from pathlib import Path
from threading import Thread

from syft_rpc.rpc import RequestMessage
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import threading
from pathspec import PathSpec

from syftbox.lib import SyftPermission
from syft_rpc import SyftBoxURL

dispatch = {}


NOT_FOUND = 404


def get_request_handler(func):
    """Process the file that is detected."""
    print("making get request handler")

    def handler(file_path, client):
        print(f"Processing file: {file_path}")
        try:
            with open(file_path, "rb") as file:
                msg = RequestMessage.load(file.read())
                print("msg.path", msg.url_path, msg.url_path in dispatch)

                response = func(msg)
                print("got response from function", response, type(response))
                body = response.content
                headers = response.headers
                status_code = response.status_code

                response_msg = msg.reply(
                    from_sender=client.email,
                    body=body,
                    headers=headers,
                    status_code=status_code,
                )
                response_msg.send(client=client)
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            print(f"Failed to process request: {file_path}. {e}")

    return handler


def file_change_handler(func):
    """Process the file that is detected."""
    print("making file_change_handler")

    def handler(file_path, client):
        print(f"Processing file: {file_path}")
        try:
            with open(file_path, "rb") as file:
                msg = RequestMessage.load(file.read())
                print("msg.path", msg.url_path, msg.url_path in dispatch)

                response = func(msg)
                print("got response from function", response, type(response))
                body = response.content
                headers = response.headers
                status_code = response.status_code

                response_msg = msg.reply(
                    from_sender=client.email,
                    body=body,
                    headers=headers,
                    status_code=status_code,
                )
                response_msg.send(client=client)
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            print(f"Failed to process request: {file_path}. {e}")

    return handler


def process_request(file_path, client):
    """Process the file that is detected."""
    try:
        print(f"Processing file: {file_path}")
        url = SyftBoxURL(file_path)
        route = url.path
        print("got a file", route)

        for spec, handler in dispatch.items():
            print("Checking spec", spec, route)
            if spec.match_file(route):
                print("found match, running handler")
                handler(file_path, client)
                return

    except Exception as e:
        import traceback

        print(traceback.format_exc())
        print(f"Failed to process request: {file_path}. {e}")


class FileWatcherHandler(FileSystemEventHandler):
    """Handles events in the watched directory."""

    def __init__(self, client):
        super().__init__()
        self.client = client

    def on_created(self, event):
        if event.is_directory:
            return
        print(f"New file detected: {event.src_path}")
        if event.src_path.endswith(".request"):
            process_request(event.src_path, self.client)


def listen(listen_path, client):
    event_handler = FileWatcherHandler(client)
    observer = Observer()
    observer.schedule(event_handler, listen_path, recursive=True)
    observer.start()
    print(f"Watching directory: {listen_path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping observer...")
        observer.stop()
    observer.join()


# Wrapper to run the listener in a thread
def start_listener_in_thread(listen_path, client):
    listener_thread = Thread(target=listen, args=(listen_path, client), daemon=True)
    listener_thread.start()
    print("File watcher started in a separate thread.")


def cleanup_old_files(listen_path: Path, message_timeout: int):
    """
    Cleans up files in the listen path that are older than 1 minute, except for the file `_.syftperm`.

    Args:
        listen_path (Path): The directory to clean up.
    """
    now = time.time()
    for file in listen_path.glob("*"):
        if file.name == "_.syftperm":
            continue
        if file.is_file():
            file_age = now - file.stat().st_mtime
            if file_age > message_timeout:  # Older than 1 minute
                try:
                    file.unlink()
                    print(f"Deleted old file: {file}")
                except Exception as e:
                    print(f"Failed to delete file {file}: {e}")


def start_cleanup_in_thread(listen_path: Path, message_timeout: int):
    """
    Starts a thread that runs the cleanup process every 1 minute.

    Args:
        listen_path (Path): The directory to clean up.
    """

    def cleanup_loop():
        while True:
            cleanup_old_files(listen_path, message_timeout)
            time.sleep(1)  # Run cleanup every 1 minute

    cleanup_thread = Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    print("Cleanup process started in a separate thread.")


class Server:
    def __init__(self, app_name: str, client, message_timeout=60):
        self.client = client
        self.datasites_path = client.datasites
        self.datasite = client.email
        self.own_datasite_path = client.datasites / client.email
        self.app_name = app_name
        self.public_listen_path = (
            self.own_datasite_path / "public" / "rpc" / self.app_name / "listen"
        )
        # create listen dir
        os.makedirs(self.public_listen_path, exist_ok=True)
        permission = SyftPermission.mine_with_public_write(email=self.datasite)
        permission.ensure(self.public_listen_path)
        start_listener_in_thread(self.public_listen_path, self.client)
        start_cleanup_in_thread(self.public_listen_path, message_timeout)
        print(f"Listening on: {self.public_listen_path}")

    def register(self, glob_path: str, func):
        print(f"Registering path: {glob_path}")
        spec = PathSpec.from_lines("gitwildmatch", [glob_path])
        dispatch[spec] = func

    def get(self, path: str):
        def decorator(function: Callable):
            func = get_request_handler(function)
            self.register(path, func)
            return function

        return decorator

    def file_change(self, path: str):
        def decorator(function: Callable):
            func = file_change_handler(function)
            self.register(path, func)
            return function

        return decorator

    async def run_forever(self):
        """Keeps the event loop running indefinitely."""
        try:
            while True:
                await asyncio.sleep(1)  # Keeps the event loop alive
        except asyncio.CancelledError:
            print("Shutting down gracefully...")

    def run(self):
        """Starts the server and blocks until interrupted."""
        loop = asyncio.get_event_loop()

        try:
            print("Server is running. Press Ctrl+C to stop.")
            loop.run_until_complete(self.run_forever())
        except KeyboardInterrupt:
            print("Keyboard interrupt received. Exiting...")
        finally:
            loop.run_until_complete(self.shutdown())
            loop.close()

    def start(self):
        """Starts the server without blocking the current thread."""
        loop = asyncio.get_event_loop()

        def start_loop():
            asyncio.set_event_loop(loop)
            print("Server started in non-blocking mode.")
            loop.run_until_complete(self.run_forever())

        # Run the event loop in a background thread
        thread = threading.Thread(target=start_loop, daemon=True)
        thread.start()

    async def shutdown(self):
        """Custom shutdown logic."""
        print("Cleaning up resources...")
