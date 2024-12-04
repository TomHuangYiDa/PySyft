import sqlite3
from pathlib import Path
from typing import List

from pydantic import BaseModel

from syftbox.lib.hash import hash_file
from syftbox.lib.permissions import ComputedPermission, PermissionRule, PermissionType
from syftbox.server.db import db
from syftbox.server.db.schema import get_db
from syftbox.server.models.sync_models import AbsolutePath, FileMetadata, RelativePath
from syftbox.server.settings import ServerSettings


class SyftFile(BaseModel):
    metadata: FileMetadata
    data: bytes
    absolute_path: AbsolutePath


def computed_permission_for_user_and_path(cursor: sqlite3.Cursor, user: str, path: Path):
    from syftbox.server.db.db import get_rules_for_path

    rules: List[PermissionRule] = get_rules_for_path(cursor, path)
    return ComputedPermission.from_user_rules_and_path(rules=rules, user=user, file_path=path)


class FileStore:
    def __init__(self, server_settings: ServerSettings) -> None:
        self.server_settings = server_settings

    @property
    def db_path(self) -> AbsolutePath:
        return self.server_settings.file_db_path

    def delete(self, path: RelativePath) -> None:
        conn = get_db(self.db_path)
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE;")
        try:
            db.delete_file_metadata(cursor, str(path))
        except ValueError:
            pass
        abs_path = self.server_settings.snapshot_folder / path
        abs_path.unlink(missing_ok=True)
        conn.commit()
        cursor.close()

    def get(self, path: RelativePath, user: str) -> SyftFile:
        with get_db(self.db_path) as conn:
            computed_perm = computed_permission_for_user_and_path(conn, user, path)
            if not computed_perm.has_permission(PermissionType.READ):
                raise PermissionError(f"User {user} does not have read permission for {path}")

            metadata = db.get_one_metadata(conn, path=str(path))
            abs_path = self.server_settings.snapshot_folder / metadata.path

            if not Path(abs_path).exists():
                self.delete(metadata.path.as_posix())
                raise ValueError("File not found")
            return SyftFile(
                metadata=metadata,
                data=self._read_bytes(abs_path),
                absolute_path=abs_path,
            )

    def exists(self, path: RelativePath) -> bool:
        with get_db(self.db_path) as conn:
            try:
                # we are skipping permission check here for now
                db.get_one_metadata(conn, path=str(path))
                return True
            except ValueError:
                return False

    def get_metadata(self, path: RelativePath, user: str) -> FileMetadata:
        with get_db(self.db_path) as conn:
            computed_perm = computed_permission_for_user_and_path(conn, user, path)
            if not computed_perm.has_permission(PermissionType.READ):
                raise PermissionError(f"User {user} does not have read permission for {path}")
            metadata = db.get_one_metadata(conn, path=str(path))
            return metadata

    def _read_bytes(self, path: AbsolutePath) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def put(self, path: Path, contents: bytes, user: str, check_permission: PermissionType) -> None:
        with get_db(self.db_path) as conn:
            computed_perm = computed_permission_for_user_and_path(conn, user, path)
            if check_permission not in [PermissionType.WRITE, PermissionType.CREATE]:
                raise ValueError(f"check_permission must be either WRITE or CREATE, got {check_permission}")

            if not computed_perm.has_permission(check_permission):
                raise PermissionError(f"User {user} does not have write permission for {path}")

            abs_path = self.server_settings.snapshot_folder / path
            abs_path.parent.mkdir(exist_ok=True, parents=True)

            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            abs_path.write_bytes(contents)
            metadata = hash_file(abs_path, root_dir=self.server_settings.snapshot_folder)
            db.save_file_metadata(cursor, metadata)
            conn.commit()
            cursor.close()

    def list_for_user(self, path: RelativePath, email: str) -> list[FileMetadata]:
        with get_db(self.db_path) as conn:
            return db.get_filemetadata_with_read_access(conn, email, path)
