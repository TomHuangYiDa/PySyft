import requests
from rich.text import Text
from textual.containers import Horizontal, Vertical
from textual.widgets import Markdown, RichLog, Static

from syftbox import __version__
from syftbox.client.base import SyftBoxContextInterface
from syftbox.tui.logs_widget import SyftLogsWidget

intro_md = """
### Welcome to SyftBox!

SyftBox is an innovative project by [OpenMined](https://openmined.org) that aims to make privacy-enhancing technologies (PETs) more accessible and user-friendly for developers. It provides a modular and intuitive framework for building PETs applications with minimal barriers, regardless of the programming language or environment.

### Important Resources
- 📚 Check the docs at https://syftbox-documentation.openmined.org/
- 📊 View the [Stats Dashboard](https://syftbox.openmined.org/datasites/andrew@openmined.org/stats.html)
- 🔧 View our [GitHub Repository](https://github.com/OpenMined/syft)
- 🔍 Browse [Available Datasets](https://syftbox.openmined.org/datasites/aggregator@openmined.org/data_search/)

Need help? Join us on [Slack](https://slack.openmined.org/) 💬
"""


class SyftTUIError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class StatusDashboard(Static):
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
        super().__init__(
            content="",
            expand=expand,
            shrink=shrink,
            markup=markup,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

    def compose(self):
        yield Static("[blue]Status[/blue]\n")
        server_url = f"[link={self.context.config.server_url}]{self.context.config.server_url}[/link]"
        client_url = f"[link={self.context.config.client_url}]{self.context.config.client_url}[/link]"
        data_dir = f"[link=file://{self.context.workspace.data_dir}]{self.context.workspace.data_dir}[/link]"
        yield Static(f"Syftbox version: [green]{__version__}[/green]")
        yield Static(f"User: [green]{self.context.email}[/green]")
        yield Static(f"Syftbox folder: [green]{data_dir}[/green]")
        yield Static(f"Server URL: [green]{server_url}[/green]")
        yield Static(f"Local URL: [green]{client_url}[/green]")

        sync_status = "🟢 [green]Active[/green]" if self._sync_is_alive() else "🔴 [red]Inactive[/red]"
        yield Static(f"Sync: {sync_status}")

        apps_count = self.count_apps()
        apps_color = "green" if apps_count > 0 else "red"
        yield Static(f"Installed APIs: [{apps_color}]{apps_count}[/{apps_color}]")

    def _sync_is_alive(self) -> bool:
        try:
            response = requests.get(f"{self.context.config.client_url}/sync/health")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    def count_apps(self) -> int:
        api_dir = self.context.workspace.apps
        return len([d for d in api_dir.iterdir() if d.is_dir() and not d.name.startswith(".")])


class HomeWidget(Static):
    DEFAULT_CSS = """
    .main {
        width: 4fr;
        padding-right: 1;
    }

    .info {
        height: 1fr;
    }

    .logs {
        height: 1fr;
        margin-top: 1;
        background: $surface;
    }

    .status {
        width: 1fr;
        height: 100%;
        background: $surface;
        margin-right: 1;
    }
    """

    def __init__(self, context: SyftBoxContextInterface) -> None:
        super().__init__()
        self.context = context
        self.logs_viewer = RichLog(
            max_lines=256,
            wrap=False,
            markup=True,
            highlight=True,
        )
        self.logs_viewer.write("[dim]Fetching logs...[/dim]")

    def _get_syftbox_logs(self) -> str:
        try:
            response = requests.get(f"{self.context.config.client_url}/logs")
            if response.status_code != 200:
                raise SyftTUIError(f"Failed to fetch logs: {response.text}")
            res = response.json()
            return "".join(res)
        except requests.exceptions.ConnectionError:
            raise SyftTUIError("Unable to connect to SyftBox")
        except Exception as e:
            raise SyftTUIError(f"Failed to fetch logs: {str(e)}")

    def write_logs(self):
        try:
            logs = self._get_syftbox_logs()
            logs = Text.from_ansi(logs)
        except SyftTUIError as e:
            logs = f"[red]{e.message}[/red]\n"
        self.logs_viewer.clear()
        self.logs_viewer.write(logs)
        self.logs_viewer.scroll_end()

    def compose(self):
        info_widget = Markdown(intro_md, classes="info")
        logs_widget = SyftLogsWidget(
            context=self.context,
            endpoint="/logs",
            title="SyftBox Logs",
            refresh_every=2,
            classes="logs",
        )

        with Horizontal():
            yield StatusDashboard(self.context, classes="status")
            yield Vertical(
                info_widget,
                logs_widget,
                classes="main",
            )
