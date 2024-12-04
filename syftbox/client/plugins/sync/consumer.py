import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from syftbox.client.exceptions import SyftServerError
from syftbox.client.plugins.sync.datasite_state import DatasiteState
from syftbox.client.plugins.sync.exceptions import FatalSyncError, SyftPermissionError, SyncEnvironmentError
from syftbox.client.plugins.sync.local_state import LocalState
from syftbox.client.plugins.sync.queue import SyncQueue, SyncQueueItem
from syftbox.client.plugins.sync.sync_action import SyncAction, determine_sync_action
from syftbox.client.plugins.sync.sync_client import SyncClient
from syftbox.client.plugins.sync.types import SyncActionType, SyncStatus
from syftbox.lib.ignore import filter_ignored_paths
from syftbox.server.sync.hash import hash_file
from syftbox.server.sync.models import FileMetadata


def create_local_batch(sync_client: SyncClient, paths_to_download: list[Path]) -> list[str]:
    try:
        content_bytes = sync_client.download_bulk(paths_to_download)
    except SyftServerError as e:
        logger.error(e)
        return []
    zip_file = zipfile.ZipFile(BytesIO(content_bytes))
    zip_file.extractall(sync_client.workspace.datasites)
    return zip_file.namelist()


class SyncConsumer:
    def __init__(self, client: SyncClient, queue: SyncQueue, local_state: LocalState):
        self.client = client
        self.queue = queue
        self.local_state = local_state

    def validate_sync_environment(self):
        if not Path(self.client.workspace.datasites).is_dir():
            raise SyncEnvironmentError("Your sync folder has been deleted by a different process.")
        if not self.local_state.path.is_file():
            raise SyncEnvironmentError("Your previous sync state has been deleted by a different process.")

    def consume_all(self):
        while not self.queue.empty():
            self.validate_sync_environment()
            item = self.queue.get(timeout=0.1)
            try:
                self.process_filechange(item)
            except FatalSyncError as e:
                # Fatal error, syncing should be interrupted
                raise e
            except Exception as e:
                logger.error(f"Failed to sync file {item.data.path}, it will be retried in the next sync. Reason: {e}")

    def download_all_missing(self, datasite_states: list[DatasiteState]):
        try:
            missing_files: list[Path] = []
            for datasite_state in datasite_states:
                for file in datasite_state.remote_state:
                    path = file.path
                    if not self.local_state.states.get(path):
                        missing_files.append(path)
            missing_files = filter_ignored_paths(self.client.workspace.datasites, missing_files)

            logger.info(f"Downloading {len(missing_files)} files in batch")
            received_files = create_local_batch(self.client, missing_files)
            for path in received_files:
                path = Path(path)
                state = self.get_current_local_metadata(path)
                self.local_state.insert_synced_file(
                    path=path,
                    state=state,
                    action=SyncActionType.CREATE_LOCAL,
                )
        except FatalSyncError as e:
            raise e
        except Exception as e:
            logger.error(
                f"Failed to download missing files, files will be downloaded individually instead. Reason: {e}"
            )

    def determine_action(self, item: SyncQueueItem) -> SyncAction:
        path = item.data.path
        local_syncstate = self.get_current_local_metadata(path)
        previous_local_syncstate = self.get_previous_local_metadata(path)
        server_syncstate = self.get_current_remote_metadata(path)

        return determine_sync_action(
            local_syncstate=local_syncstate,
            previous_local_syncstate=previous_local_syncstate,
            server_syncstate=server_syncstate,
        )

    def process_action(self, action: SyncAction) -> None:
        if action.is_noop():
            return

        logger.info(action.info_message)
        try:
            action.execute(self.client)
        except SyftPermissionError as e:
            action.reject(self.client, reason=str(e))
        except (SyftServerError, httpx.RequestError) as e:
            # Unknown server error or connection error, retry next sync
            action.error(e)

    def write_to_local_state(self, action: SyncAction) -> None:
        if action.action_type == SyncActionType.NOOP:
            return

        if action.status == SyncStatus.SYNCED:
            self.local_state.insert_synced_file(
                path=action.path,
                state=action.result_local_state,
                action=action.action_type,
            )
        else:
            self.local_state.insert_status_info(
                path=action.path,
                status=action.status,
                message=action.message,
                action=action.action_type,
            )

    def process_filechange(self, item: SyncQueueItem) -> None:
        action = self.determine_action(item)
        self.process_action(action)
        self.write_to_local_state(action)

    def get_current_local_metadata(self, path: Path) -> Optional[FileMetadata]:
        abs_path = self.client.workspace.datasites / path
        if not abs_path.is_file():
            return None
        return hash_file(abs_path, root_dir=self.client.workspace.datasites)

    def get_previous_local_metadata(self, path: Path) -> Optional[FileMetadata]:
        return self.local_state.states.get(path, None)

    def get_current_remote_metadata(self, path: Path) -> Optional[FileMetadata]:
        try:
            return self.client.get_metadata(path)
        except SyftServerError:
            return None
