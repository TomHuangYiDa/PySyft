# copied from syft_core/url.py and workspace.py

import os
import re
from pathlib import Path
from urllib.parse import urlencode, urlparse

from typing import Iterable, Union
from typing_extensions import TypeAlias

PathLike: TypeAlias = Union[str, os.PathLike, Path]
UserLike: TypeAlias = Union[str, Iterable[str]]


def to_path(path: PathLike) -> Path:
    return Path(path).expanduser().resolve()


class SyftWorkspace:
    """
    A Syft workspace is a directory structure for everything stored by the client.
    Each workspace is expected to be unique for a client.

    ```txt
        data_dir/
        ├── apis/                       <-- installed apis
        ├── plugins/                    <-- plugins data
        └── datasites/                  <-- synced datasites
            ├── user1@openmined.org/
            │   └── api_data/
            └── user2@openmined.org/
                └── api_data/
    ```
    """

    def __init__(self, data_dir: PathLike):
        self.data_dir = to_path(data_dir)
        """Path to the root directory of the workspace."""

        # datasites dir
        self.datasites = self.data_dir / "datasites"
        """Path to the directory containing datasites."""

        # plugins dir
        """Path to the directory containing plugins."""
        self.plugins = self.data_dir / "plugins"

        # apps/apis dir
        self.apps = self.data_dir / "apis"
        """Path to the directory containing apps."""

    def mkdirs(self) -> None:
        self.datasites.mkdir(parents=True, exist_ok=True)
        self.plugins.mkdir(parents=True, exist_ok=True)
        self.apps.mkdir(parents=True, exist_ok=True)


class SyftBoxURL:
    def __init__(self, url: str):
        if isinstance(url, SyftBoxURL):
            url = str(url)
        elif not SyftBoxURL.is_valid(url):
            raise ValueError(f"Invalid SyftBoxURL: {url}")

        self.url = url
        self.parsed = urlparse(self.url)

    @classmethod
    def is_valid(self, url: str):
        """Validates the given URL matches the syft:// protocol and email-based schema."""
        pattern = r"^syft://([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)(/.*)?$"
        return re.match(pattern, url)

    @property
    def protocol(self):
        """Returns the protocol (syft://)."""
        return self.parsed.scheme + "://"

    @property
    def host(self):
        """Returns the host, which is the email part."""
        return self.parsed.netloc

    @property
    def path(self):
        """Returns the path component after the email."""
        return self.parsed.path

    def to_local_path(self, datasites_path: PathLike) -> Path:
        """
        Converts the SyftBoxURL to a local file system path.
        Args:
            datasites_path (Path): Base directory for datasites.
        Returns:
            Path: Local file system path.
        """
        # Remove the protocol and prepend the datasites_path
        local_path = to_path(datasites_path) / self.host / self.path.lstrip("/")
        return local_path.resolve()

    def as_http_params(self) -> dict[str, str]:
        return {
            "method": "get",
            "datasite": self.host,
            "path": self.path,
        }

    def to_http_get(self, rpc_url: str) -> str:
        rpc_url = rpc_url.split("//")[-1]
        params = self.as_http_params()
        url_params = urlencode(params)
        http_url = f"http://{rpc_url}?{url_params}"
        return http_url

    def from_path(self, path: PathLike, workspace: SyftWorkspace) -> str:
        rel_path = to_path(path).relative_to(workspace.datasites)
        return f"syft://{rel_path}"

    def __repr__(self):
        return self.url



if __name__ == "__main__":
    syftbox_url = SyftBoxURL("syft://khoa@openmined.org/public/apps/chat")
    print(syftbox_url.parsed)
    print(syftbox_url.to_local_path(Path("~/SyftBox/datasites")))
    print(syftbox_url.as_http_params())
    print(
        syftbox_url.from_path(
            "~/SyftBox/datasites/test@openmined.org/public/some/path",
            SyftWorkspace(Path("~/SyftBox")),
        )
    )
    import pdb; pdb.set_trace()