from typing import Optional

import requests
from rich.text import Text
from textual.containers import Vertical
from textual.widgets import RichLog, Static

from syftbox.lib import Client


class SyftTUIError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class SyftLogsWidget(Static):
    def __init__(
        self,
        context: Client,
        endpoint: str,
        title: Optional[str] = None,
        refresh_every: int = 2,
        classes: str | None = None,
    ) -> None:
        super().__init__(classes=classes)
        self.context = context
        self.endpoint = endpoint
        self.title = title
        self.refresh_every = refresh_every
        self.logs_viewer = RichLog(
            max_lines=256,
            wrap=False,
            markup=True,
            highlight=True,
        )
        self.logs_viewer.write("[dim]Fetching logs...[/dim]")

    def _get_err(self, response: requests.Response) -> str:
        try:
            return response.json()["detail"]
        except Exception:
            return response.text

    def _fetch_logs(self) -> str:
        try:
            response = requests.get(f"{self.context.config.client_url}{self.endpoint}")
            if response.status_code != 200:
                raise SyftTUIError({self._get_err(response)})
            logs = response.json()["logs"]
            return "".join(logs)
        except requests.exceptions.ConnectionError:
            raise SyftTUIError("Unable to connect to SyftBox")
        except Exception as e:
            raise SyftTUIError(f"Failed to fetch logs: {str(e)}")

    def refresh_logs(self) -> None:
        try:
            logs = self._fetch_logs()
            logs = Text.from_ansi(logs)
        except SyftTUIError as e:
            logs = f"[red]{e.message}[/red]\n"
        self.logs_viewer.clear()
        self.logs_viewer.write(logs)
        self.logs_viewer.scroll_end(animate=False)

    def compose(self):
        with Vertical():
            if self.title:
                yield Static(f"[blue]{self.title}[/blue]\n")
            yield self.logs_viewer

        self.refresh_logs()
        if self.refresh_every > 0:
            self.set_interval(self.refresh_every, self.refresh_logs)
