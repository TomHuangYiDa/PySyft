import re
from pathlib import Path
from urllib.parse import urlencode, urlparse

from syft_core.types import PathLike, to_path
from syft_core.workspace import SyftWorkspace


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

    @classmethod
    def from_path(cls, path: PathLike, workspace: SyftWorkspace) -> str:
        rel_path = to_path(path).relative_to(workspace.datasites)
        return cls(f"syft://{rel_path}")

    def __repr__(self):
        return self.url


if __name__ == "__main__":
    syftbox_url = SyftBoxURL("syft://info@domain.com/datasite1")
    print(syftbox_url.parsed)
    print(syftbox_url.to_local_path(Path("~/SyftBox/datasites")))
    print(syftbox_url.as_http_params())
    print(
        syftbox_url.from_path(
            "~/SyftBox/datasites/test@openmined.org/public/some/path",
            SyftWorkspace(Path("~/SyftBox")),
        )
    )
