import base64
from pathlib import Path
from typing import Union

import httpx
from pydantic import BaseModel
from tqdm import tqdm

from syftbox.client.base import SyftClientInterface
from syftbox.client.exceptions import SyftServerError
from syftbox.client.plugins.sync.exceptions import SyftPermissionError
from syftbox.lib.workspace import SyftWorkspace
from syftbox.server.models.sync_models import ApplyDiffResponse, DiffResponse, FileMetadata, RelativePath


class StreamedFile(BaseModel):
    path: RelativePath
    content: str

    @property
    def raw_bytes(self) -> bytes:
        return base64.b64decode(self.content)

    def write_bytes(self, output_dir: Path):
        file_path = output_dir / self.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(self.raw_bytes)


class SyncClient:
    """
    Client for handling file sync operations with the server.
    """

    def __init__(self, client: SyftClientInterface) -> None:
        self.client = client

    @property
    def email(self) -> str:
        return self.client.email

    @property
    def server_client(self) -> httpx.Client:
        return self.client.server_client

    @property
    def workspace(self) -> SyftWorkspace:
        return self.client.workspace

    def whoami(self) -> str:
        return self.client.whoami()

    def raise_for_status(self, response: httpx.Response) -> None:
        """Implements response error handling for all sync operations."""
        endpoint_path = response.url.path
        if response.status_code == 403:
            raise SyftPermissionError(f"[{endpoint_path}] permission denied: {response.text}")
        elif response.status_code != 200:
            raise SyftServerError(f"[{endpoint_path}] call failed ({response.status_code}): {response.text}")

    def get_datasite_states(self) -> dict[str, list[FileMetadata]]:
        response = self.server_client.post("/sync/datasite_states")
        self.raise_for_status(response)
        data = response.json()

        result = {}
        for email, metadata_list in data.items():
            result[email] = [FileMetadata(**item) for item in metadata_list]

        return result

    def get_remote_state(self, relative_path: Path) -> list[FileMetadata]:
        response = self.server_client.post(
            "/sync/dir_state",
            params={"dir": relative_path.as_posix()},
        )
        self.raise_for_status(response)
        data = response.json()
        return [FileMetadata(**item) for item in data]

    def get_metadata(self, path: Path) -> FileMetadata:
        response = self.server_client.post(
            "/sync/get_metadata",
            json={"path": path.as_posix()},
        )
        self.raise_for_status(response)
        return FileMetadata(**response.json())

    def get_diff(self, relative_path: Path, signature: Union[str, bytes]) -> DiffResponse:
        """Get rsync-style diff between local and remote file.

        Args:
            relative_path: Path to file relative to workspace root
            signature: b85 encoded signature of the local file

        Returns:
            DiffResponse containing the diff and expected hash
        """
        if not isinstance(signature, str):
            signature = base64.b85encode(signature).decode("utf-8")

        response = self.server_client.post(
            "/sync/get_diff",
            json={
                "path": relative_path.as_posix(),
                "signature": signature,
            },
        )

        self.raise_for_status(response)
        return DiffResponse(**response.json())

    def apply_diff(self, relative_path: Path, diff: Union[str, bytes], expected_hash: str) -> ApplyDiffResponse:
        """Apply an rsync-style diff to update a remote file.

        Args:
            relative_path: Path to file relative to workspace root
            diff: py_fast_rsync binary diff to apply
            expected_hash: Expected hash of the file after applying diff, used for verification.

        Returns:
            ApplyDiffResponse containing the result of applying the diff
        """
        if not isinstance(diff, str):
            diff = base64.b85encode(diff).decode("utf-8")

        response = self.server_client.post(
            "/sync/apply_diff",
            json={
                "path": relative_path.as_posix(),
                "diff": diff,
                "expected_hash": expected_hash,
            },
        )

        self.raise_for_status(response)
        return ApplyDiffResponse(**response.json())

    def delete(self, relative_path: Path) -> None:
        response = self.server_client.post(
            "/sync/delete",
            json={"path": relative_path.as_posix()},
        )
        self.raise_for_status(response)

    def create(self, relative_path: Path, data: bytes) -> None:
        response = self.server_client.post(
            "/sync/create",
            files={"file": (relative_path.as_posix(), data, "text/plain")},
        )
        self.raise_for_status(response)

    def download(self, relative_path: Path) -> bytes:
        response = self.server_client.post(
            "/sync/download",
            json={"path": relative_path.as_posix()},
        )
        self.raise_for_status(response)
        return response.content

    def download_files_streaming(self, relative_paths: list[str], output_dir: Path) -> None:
        relative_paths = [path.as_posix() for path in relative_paths]

        with self.server_client.stream(
            "POST",
            "/sync/download_bulk",
            json={"paths": relative_paths},
        ) as response:
            response.raise_for_status()

            extracted_files = []
            for line in tqdm(
                response.iter_lines(),
                total=len(relative_paths),
                unit="files",
                desc="Downloading files",
            ):
                file = StreamedFile.model_validate_json(line)
                file.write_bytes(output_dir)
                extracted_files.append(file.path)

            return extracted_files
