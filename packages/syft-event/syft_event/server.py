import asyncio
import os
import time
from collections.abc import Callable
from pathlib import Path
from threading import Thread
from typing import Type
from syft_rpc.rpc import RequestMessage
from watchdog.events import FileSystemEventHandler
from watchdog.events import (
    FileSystemEvent,
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileDeletedEvent,
    DirCreatedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    DirDeletedEvent,
)
from watchdog.observers import Observer
import threading
from pathspec import PathSpec
from pydantic import BaseModel, ConfigDict


from syftbox.lib import SyftPermission
from syft_rpc import SyftBoxURL

dispatch = {}

ALL_EVENTS = [
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileDeletedEvent,
    DirCreatedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    DirDeletedEvent,
]

NOT_FOUND = 404


def get_request_handler(func):
    """Process the file that is detected."""
    # print("making get request handler")

    def handler(event, client):
        # print(f"Processing file: {event.src_path}")
        try:
            with open(event.src_path, "rb") as file:
                msg = RequestMessage.load(file.read())
                # print("msg.path", msg.url_path, msg.url_path in dispatch)

                response = func(msg)
                # print("got response from function", response, type(response))
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
            print(f"Failed to process request: {event.src_path}. {e}")

    return handler


def file_change_handler(func):
    """Process the file that is detected."""
    # print("making file_change_handler")

    def handler(event, client):
        # print(f"Processing file: {event.src_path}")
        try:
            func(event)
        except Exception as e:
            import traceback

            print(traceback.format_exc())
            print(f"Failed to process request: {event.src_path}. {e}")

    return handler


class RouteMatch(BaseModel):
    raw_glob_path: str
    handler: Callable
    events: list[Type[FileSystemEvent]]
    glob_path: str | None = None
    spec_cache: PathSpec | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def match_and_run(self, event: FileSystemEvent, client):
        # print("match and run event", type(event), event)
        if type(event) not in self.events:
            # print(f"> ignoring {self.raw_glob_path} {event} not in {self.events}")
            return False

        if self.spec_cache is None:
            spec = PathSpec.from_lines("gitwildmatch", [self.glob_path])
            self.spec_cache = spec
        else:
            # print("<><><> Got cached spec")
            pass

        syft_path = "syft://" + str(event.src_path).replace(
            str(client.datasites) + "/", ""
        )
        url = SyftBoxURL(syft_path)
        route = url.host + url.path
        if not self.spec_cache.match_file(route):
            # print(
            #     f"> ignoring {self.raw_glob_path} {route} doesn't match {self.glob_path}"
            # )
            return False
        return self.handler(event, client)


def process_request(event, client):
    """Process the file that is detected."""
    try:
        file_path = event.src_path
        # print(f"> Processing file event: {event}: {file_path}", client.datasites)

        for _, matcher in dispatch.items():
            # print(">>> got event", event, type(event))
            matcher.match_and_run(event, client)

    except Exception as e:
        import traceback

        print(traceback.format_exc())
        print(f"Failed to process request: {file_path}. {e}")


class FileWatcherHandler(FileSystemEventHandler):
    """Handles events in the watched directory."""

    def __init__(self, client):
        super().__init__()
        self.client = client

    def on_any_event(self, event):
        if event.is_directory:
            return
        # print(f"File Change detected: {event} {event.src_path}")
        # if event.src_path.endswith(".request"):
        process_request(event, self.client)


def listen(listen_path, client):
    print("> Listening to listen_path", listen_path)
    event_handler = FileWatcherHandler(client)
    observer = Observer()
    observer.schedule(event_handler, listen_path, recursive=True)
    observer.start()
    # print(f"Watching directory: {listen_path}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping observer...")
        observer.stop()
    observer.join()


def start_listener_in_thread(listen_path, client):
    """Starts a file listener in a separate thread and returns:
    listener_thread, observer, stop_event
    """

    stop_event = threading.Event()
    observer = Observer()
    event_handler = FileWatcherHandler(client)
    observer.schedule(event_handler, listen_path, recursive=True)

    def listen():
        observer.start()
        print(f"> Watching directory: {listen_path}")
        # Loop until stop_event is set
        while not stop_event.is_set():
            time.sleep(1)
        # On shutdown, stop and join observer
        observer.stop()
        observer.join()

    listener_thread = Thread(target=listen, daemon=True)
    listener_thread.start()
    return listener_thread, observer, stop_event


def cleanup_old_files(listen_path: Path, message_timeout: int):
    now = time.time()
    for file in listen_path.glob("*"):
        if file.name == "_.syftperm":
            continue
        if file.is_file():
            file_age = now - file.stat().st_mtime
            if file_age > message_timeout:
                try:
                    file.unlink()
                    print(f"Deleted old file: {file}")
                except Exception as e:
                    print(f"Failed to delete file {file}: {e}")


def start_cleanup_in_thread(listen_path: Path, message_timeout: int):
    """Starts the cleanup loop in a thread and returns the thread and a stop_event."""

    stop_event = threading.Event()

    def cleanup_loop():
        while not stop_event.is_set():
            cleanup_old_files(listen_path, message_timeout)
            time.sleep(1)  # Run cleanup every 1 minute

    cleanup_thread = Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    return cleanup_thread, stop_event


THREADS_STARTED = False


class Server:
    def __init__(self, app_name: str, client, message_timeout=60):
        self.client = client
        self.datasites_path = client.datasites
        self.datasite = client.email
        self.message_timeout = message_timeout
        self.app_name = app_name
        self.public_listen_path = client.datasites
        os.makedirs(self.public_listen_path, exist_ok=True)
        permission = SyftPermission.mine_with_public_write(email=self.datasite)
        permission.ensure(self.public_listen_path)

        # References to threads and stop events
        self.listener_thread = None
        self.observer = None
        self.listener_stop_event = None
        self.cleanup_thread = None
        self.cleanup_stop_event = None
        self.server_thread = None

    def start_threads(self):
        """Starts the listener thread, cleanup thread, and the event loop in a background thread,
        mimicking what the old `start()` method did."""
        global THREADS_STARTED
        if THREADS_STARTED:
            print("Threads already started in this process, skipping.")
            return
        THREADS_STARTED = True

        # Start the file listener and cleanup threads
        self.listener_thread, self.observer, self.listener_stop_event = (
            start_listener_in_thread(self.public_listen_path, self.client)
        )
        self.cleanup_thread, self.cleanup_stop_event = start_cleanup_in_thread(
            self.public_listen_path, self.message_timeout
        )

        def start_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(self.run_forever())

        self.server_thread = threading.Thread(target=start_loop, daemon=True)
        self.server_thread.start()

    def register(self, glob_path: str, func, events: list[FileSystemEvent] = None):
        if events is None:
            events = ALL_EVENTS

        replacements = {"datasite": self.client.email}
        templated_glob_path = glob_path.format(**replacements)

        matcher = RouteMatch(
            raw_glob_path=glob_path,
            glob_path=templated_glob_path,
            handler=func,
            events=events,
        )

        print(f"Registering path: {glob_path}")
        dispatch[glob_path] = matcher

    def get(self, path: str):
        def decorator(function: Callable):
            func = get_request_handler(function)
            self.register(path, func, events=[FileCreatedEvent])
            return function

        return decorator

    def file_change(self, path: str, events: list[Type[FileSystemEvent]] = None):
        def decorator(function: Callable):
            func = file_change_handler(function)
            self.register(path, func, events=events)
            return function

        return decorator

    async def run_forever(self):
        """Keeps the event loop running indefinitely."""
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("Shutting down gracefully...")

    def block(self):
        """This method can block until interrupted if you need it."""
        loop = asyncio.get_event_loop()
        try:
            print("Server is running. Press Ctrl+C to stop.")
            loop.run_until_complete(self.run_forever())
        except KeyboardInterrupt:
            print("Keyboard interrupt received. Exiting...")
        finally:
            loop.run_until_complete(self.shutdown())
            loop.close()

    async def shutdown(self):
        """Shuts down the server gracefully by stopping threads and the event loop."""
        print("Cleaning up resources...")

        # Stop the cleanup thread
        if self.cleanup_stop_event is not None:
            self.cleanup_stop_event.set()
            if self.cleanup_thread is not None:
                self.cleanup_thread.join()

        # Stop the listener thread
        if self.listener_stop_event is not None:
            self.listener_stop_event.set()
            if self.listener_thread is not None:
                self.listener_thread.join()

        # Stop event loop tasks
        loop = asyncio.get_event_loop()
        tasks = [
            t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)
        ]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()
        loop.close()

        # Wait for the server thread (event loop thread) if needed
        if self.server_thread is not None and self.server_thread.is_alive():
            self.server_thread.join()
