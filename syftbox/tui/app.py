from textual.app import App
from textual.widgets import Footer, Header, TabbedContent, TabPane

from syftbox.client.base import SyftBoxContextInterface
from syftbox.tui.api_widget import APIWidget
from syftbox.tui.datasites_widget import DatasiteSelector
from syftbox.tui.home_widget import HomeWidget
from syftbox.tui.sync_widget import SyncWidget


class SyftBoxTUI(App):
    BINDINGS = [
        ("h", "switch_tab('Home')", "Home"),
        ("a", "switch_tab('APIs')", "APIs"),
        ("d", "switch_tab('Datasites')", "Datasites"),
        ("s", "switch_tab('Sync')", "Sync"),
    ]

    def __init__(
        self,
        syftbox_context: SyftBoxContextInterface,
        driver_class=None,
        css_path=None,
        watch_css=False,
        ansi_color=False,
    ):
        self.syftbox_context = syftbox_context
        super().__init__(driver_class, css_path, watch_css, ansi_color)

    def action_toggle_dark(self) -> None:
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"

    def action_switch_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab
        self.query_one(TabbedContent).active_pane.children[0].focus()

    def on_mount(self) -> None:
        self.title = "SyftBox"

    def compose(self):
        yield Header(name="SyftBox")
        with TabbedContent():
            with TabPane("Home", id="Home"):
                yield HomeWidget(self.syftbox_context)
            with TabPane("APIs", id="APIs"):
                yield APIWidget(self.syftbox_context)
            with TabPane("Datasites", id="Datasites"):
                yield DatasiteSelector(
                    base_path=self.syftbox_context.workspace.datasites,
                    default_datasite=self.syftbox_context.email,
                )
            with TabPane("Sync", id="Sync"):
                yield SyncWidget(self.syftbox_context)
        yield Footer()
