import re
from pathlib import Path
from typing import Dict
from urllib.parse import ParseResult, urlencode, urlparse

from pydantic import BaseModel, computed_field, field_validator

from syft_core.types import PathLike, to_path
from syft_core.workspace import SyftWorkspace


class SyftBoxURL(BaseModel):
    url: str

    # Configure Pydantic to use property getters
    model_config = {
        "validate_assignment": True,
        "frozen": True,  # Make the model immutable like the original class
    }

    @field_validator("url")
    def validate_url(cls, url: str) -> str:
        """Validates the given URL matches the syft:// protocol and email-based schema."""
        if isinstance(url, SyftBoxURL):
            url = str(url)

        pattern = r"^syft://([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)(/.*)?$"
        if not re.match(pattern, url):
            raise ValueError(f"Invalid SyftBoxURL: {url}")
        return url

    @computed_field
    def parsed(self) -> ParseResult:
        """Returns the parsed URL components."""
        return urlparse(self.url)

    @computed_field
    def protocol(self) -> str:
        """Returns the protocol (syft://)."""
        return self.parsed.scheme + "://"

    @computed_field
    def host(self) -> str:
        """Returns the host, which is the email part."""
        return self.parsed.netloc

    @computed_field
    def path(self) -> str:
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

    def as_http_params(self) -> Dict[str, str]:
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
    def from_path(cls, path: PathLike, workspace: SyftWorkspace) -> "SyftBoxURL":
        rel_path = to_path(path).relative_to(workspace.datasites)
        return cls(url=f"syft://{rel_path}")

    def __str__(self) -> str:
        return self.url

    def __repr__(self) -> str:
        return self.url


if __name__ == "__main__":
    # Example usage
    syftbox_url = SyftBoxURL(url="syft://info@domain.com/datasite1")
    print(syftbox_url.parsed)
    print(syftbox_url.to_local_path(Path("~/SyftBox/datasites")))
    print(syftbox_url.as_http_params())
    print(
        syftbox_url.from_path(
            "~/SyftBox/datasites/test@openmined.org/public/some/path",
            SyftWorkspace(Path("~/SyftBox")),
        )
    )
