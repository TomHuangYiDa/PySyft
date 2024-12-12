from pathlib import Path
from typing import Annotated, Optional

from typer import Context, Option, Typer

from syftbox.server.migrations import run_migrations
from syftbox.server.settings import ServerSettings

app = Typer(
    name="SyftBox Server",
    pretty_exceptions_enable=False,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


# Define options separately to keep the function signature clean
# fmt: off
SERVER_PANEL = "Server Options"
SSL_PANEL = "SSL Options"

PORT_OPTS = Option(
    "-p", "--port",
    rich_help_panel=SERVER_PANEL,
    help="Local port for the SyftBox client",
)
WORKERS_OPTS = Option(
    "-w", "--workers",
    rich_help_panel=SERVER_PANEL,
    help="Number of worker processes",
)
VERBOSE_OPTS = Option(
    "-v", "--verbose",
    is_flag=True,
    rich_help_panel=SERVER_PANEL,
    help="Enable verbose mode",
)
RELOAD_OPTS = Option(
    "--reload", "--debug",
    rich_help_panel=SERVER_PANEL,
    help="Enable debug mode",
)
EMAIL_OPTS = Option(
    "-e", "--email",
    rich_help_panel=SERVER_PANEL,
    help="Email to ban/unban",
)
SSL_KEY_OPTS = Option(
    "--key", "--ssl-keyfile",
    exists=True, file_okay=True, readable=True,
    rich_help_panel=SSL_PANEL,
    help="Path to SSL key file",
)
SSL_CERT_OPTS = Option(
    "--cert", "--ssl-certfile",
    exists=True, file_okay=True, readable=True,
    rich_help_panel=SSL_PANEL,
    help="Path to SSL certificate file",
)

RELOAD_OPTS = Option(
    "--reload",
    is_flag=True,
    help="Reload the server on file changes",
)

RELOAD_DIR_OPTS = Option(
    "--reload-dir",
    help="Directories to watch for file changes",
)
# fmt: on


@app.callback(invoke_without_command=True)
def server(
    ctx: Context,
    port: Annotated[int, PORT_OPTS] = 5001,
    workers: Annotated[int, WORKERS_OPTS] = 1,
    verbose: Annotated[bool, VERBOSE_OPTS] = False,
    ssl_key: Annotated[Optional[Path], SSL_KEY_OPTS] = None,
    ssl_cert: Annotated[Optional[Path], SSL_CERT_OPTS] = None,
    reload: Annotated[bool, RELOAD_OPTS] = False,
    reload_dir: Annotated[Optional[str], RELOAD_DIR_OPTS] = None,
):
    """Run the SyftBox server"""

    if ctx.invoked_subcommand is not None:
        return

    # lazy import to improve CLI startup performance
    import uvicorn

    settings = ServerSettings()
    run_migrations(settings)

    uvicorn.run(
        app="syftbox.server.server:app",
        host="0.0.0.0",
        port=port,
        log_level="debug" if verbose else "info",
        workers=workers,
        ssl_keyfile=ssl_key,
        ssl_certfile=ssl_cert,
        timeout_graceful_shutdown=5,
        reload=reload,
        reload_dirs=reload_dir,
    )


def main():
    app()


if __name__ == "__main__":
    main()
