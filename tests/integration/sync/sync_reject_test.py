from pathlib import Path

import faker
import yaml
from fastapi.testclient import TestClient

from syftbox.client.base import SyftClientInterface
from syftbox.client.plugins.sync.manager import SyncManager
from syftbox.client.plugins.sync.sync_action import format_rejected_path
from syftbox.client.utils.dir_tree import DirTree, create_dir_tree
from syftbox.lib.constants import PERM_FILE
from syftbox.lib.permissions import PermissionFile
from syftbox.server.settings import ServerSettings

fake = faker.Faker()


def assert_files_not_on_datasite(client: SyftClientInterface, files: list[Path]):
    for file in files:
        assert not (client.workspace.datasites / file).exists(), f"File {file} exists on datasite {client.email}"


def assert_files_on_datasite(client: SyftClientInterface, files: list[Path]):
    for file in files:
        assert (client.workspace.datasites / file).exists(), f"File {file} does not exist on datasite {client.email}"


def assert_files_on_server(server_client: TestClient, files: list[Path]):
    server_settings: ServerSettings = server_client.app_state["server_settings"]
    for file in files:
        assert (server_settings.snapshot_folder / file).exists(), f"File {file} does not exist on server"


def assert_dirtree_exists(base_path: Path, tree: DirTree) -> None:
    for name, content in tree.items():
        local_path = base_path / name

        if isinstance(content, str):
            assert local_path.read_text() == content
        elif isinstance(content, PermissionFile):
            assert yaml.safe_load(local_path.read_text()) == content.to_dict()
        elif isinstance(content, dict):
            assert local_path.is_dir()
            assert_dirtree_exists(local_path, content)


def test_create_without_permission(
    server_client: TestClient, datasite_1: SyftClientInterface, datasite_2: SyftClientInterface
):
    # server_settings: ServerSettings = server_client.app_state["server_settings"]
    sync_service_1 = SyncManager(datasite_1)
    sync_service_2 = SyncManager(datasite_2)

    # Create a folder with only read permission for datasite_2
    tree = {
        "folder_1": {
            PERM_FILE: PermissionFile.mine_with_public_read(datasite_1.email, Path("folder1") / PERM_FILE),
        },
    }
    create_dir_tree(Path(datasite_1.datasite), tree)

    sync_service_1.run_single_thread()
    sync_service_2.run_single_thread()

    folder_on_ds1 = datasite_1.workspace.datasites / datasite_1.email / "folder_1"
    folder_on_ds2 = datasite_2.workspace.datasites / datasite_1.email / "folder_1"

    # check if datasite_1/folder_1/PERM_FILE exists on datasite_2
    assert (folder_on_ds2 / PERM_FILE).exists()

    # create a file in folder_1 and sync
    new_file = folder_on_ds2 / "file.txt"
    new_file.write_text("Hello, World!")

    # TODO server currently does not return 403, but unhandled exception
    sync_service_2.run_single_thread()
    sync_service_1.run_single_thread()

    # creating file.txt has been rejected
    assert not (folder_on_ds1 / "file.txt").exists()
    assert not (folder_on_ds2 / "file.txt").exists()
    assert format_rejected_path(folder_on_ds2 / "file.txt").exists()

    # rejected file does not get synced
    sync_service_2.run_single_thread()
    sync_service_1.run_single_thread()
    assert not (folder_on_ds1 / "file.txt.rejected").exists()


def test_delete_without_permission(
    server_client: TestClient, datasite_1: SyftClientInterface, datasite_2: SyftClientInterface
):
    # server_settings: ServerSettings = server_client.app_state["server_settings"]
    sync_service_1 = SyncManager(datasite_1)
    sync_service_2 = SyncManager(datasite_2)

    # Create a folder with only read permission for datasite_2
    tree = {
        "folder_1": {
            PERM_FILE: PermissionFile.mine_with_public_read(datasite_1.email, Path("folder1") / PERM_FILE),
            "file.txt": "Hello, World!",
        },
    }
    create_dir_tree(Path(datasite_1.datasite), tree)

    sync_service_1.run_single_thread()
    sync_service_2.run_single_thread()

    folder_on_ds1 = datasite_1.workspace.datasites / datasite_1.email / "folder_1"
    folder_on_ds2 = datasite_2.workspace.datasites / datasite_1.email / "folder_1"

    # Delete file.txt on datasite_2 is rejected
    (folder_on_ds2 / "file.txt").unlink(missing_ok=False)
    sync_service_2.run_single_thread()
    sync_service_1.run_single_thread()

    assert (folder_on_ds1 / "file.txt").exists()
    assert (folder_on_ds2 / "file.txt").exists()


def test_modify_without_permissions(
    server_client: TestClient, datasite_1: SyftClientInterface, datasite_2: SyftClientInterface
):
    raise NotImplementedError
