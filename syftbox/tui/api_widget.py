import datetime
import random
import urllib
import urllib.parse

import faker
from textual.containers import Horizontal
from textual.widgets import Label, ListItem, ListView, Static

from syftbox.client.base import SyftBoxContextInterface
from syftbox.tui.logs_widget import SyftLogsWidget


def generate_random_loguru_logs(app: str, num_lines: int) -> str:
    now = datetime.datetime.now()
    times = [now - datetime.timedelta(seconds=i) for i in range(num_lines)]
    log_levels = ["INFO", "WARNING"]
    messages = []
    for time in times:
        log_level = random.choice(log_levels)
        message = faker.Faker().sentence()
        messages.append(f"{time} | {log_level} | {app.upper()}: {message}")
    return "\n".join(messages)


class APIWidget(Static):
    DEFAULT_CSS = """
    .sidebar {
        margin-right: 1;
        width: 1fr;
    }

    .logs {
        width: 4fr;
        height: 100%;
        background: $surface;
    }

    """

    def __init__(
        self,
        context: SyftBoxContextInterface,
        *,
        expand=False,
        shrink=False,
        markup=True,
        name=None,
        id=None,
        classes=None,
        disabled=False,
    ):
        self.context = context
        self.apps = []
        super().__init__(
            "",
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

    def compose(self):
        self.apps = self.get_installed_apps()

        with Horizontal():
            list_view = ListView(*[ListItem(Label(app), id=app) for app in self.apps], classes="sidebar")
            list_view.styles.width = "20%"
            yield list_view

            self.log_widget = SyftLogsWidget(self.context, None, title="API Logs", refresh_every=2, classes="logs")
            self.set_app_logs(self.apps[0])

            yield self.log_widget

    def set_app_logs(self, app_name: str) -> None:
        # urlencoded
        app_name = urllib.parse.quote(app_name)
        endpoint = f"/apps/logs/{app_name}"
        self.log_widget.endpoint = endpoint
        self.log_widget.refresh_logs()

    def get_installed_apps(self) -> list[str]:
        api_dir = self.context.workspace.apps
        return [d.name for d in api_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        app_name = event.item.id
        self.set_app_logs(app_name)
