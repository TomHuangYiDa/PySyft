from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from watchdog.events import FileSystemEvent, FileSystemEventHandler

__all__ = ["RpcRequestHandler", "AnyPatternHandler"]


class PatternMatchingHandler(FileSystemEventHandler):
    def __init__(self, patterns: list[str], ignore_directory: bool = True):
        self.spec = PathSpec.from_lines(GitWildMatchPattern, patterns)
        self.patterns = patterns
        self.ignore_directory = ignore_directory

    def dispatch(self, event: FileSystemEvent) -> None:
        if self.ignore_directory and event.is_directory:
            return
        if self.spec.match_file(event.src_path):
            super().dispatch(event)


class RpcRequestHandler(PatternMatchingHandler):
    def __init__(self, handler):
        super().__init__(patterns=["**/*.request"])
        self.handler = handler

    def on_any_event(self, event: FileSystemEvent):
        self.handler(event)


class AnyPatternHandler(PatternMatchingHandler):
    def __init__(self, patterns, handler):
        super().__init__(patterns)
        self.handler = handler

    def on_any_event(self, event: FileSystemEvent):
        self.handler(event)
