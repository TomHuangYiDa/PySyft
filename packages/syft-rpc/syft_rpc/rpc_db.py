from __future__ import annotations

import sqlite3
import threading
from functools import cache
from uuid import UUID

from syft_core.client_shim import Client
from typing_extensions import Optional, Union

from syft_rpc.protocol import SyftFuture

__Q_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS futures (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    expires TIMESTAMP NOT NULL,
    namespace TEXT NOT NULL
) WITHOUT ROWID
"""

__Q_INSERT_FUTURE = """
INSERT OR REPLACE INTO futures (id, path, expires, namespace)
VALUES (:id, :path, :expires, :namespace)
"""


thread_local = threading.local()


@cache
def get_default_client():
    return Client.load()


def __get_connection(client: Client) -> sqlite3.Connection:
    if not hasattr(thread_local, "conn"):
        db_dir = client.workspace.plugins
        db_dir.mkdir(exist_ok=True, parents=True)
        db_path = db_dir / "rpc.futures.db"
        conn = sqlite3.connect(str(db_path))

        # Multi-process optimizations for small writes
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and speed
        conn.execute("PRAGMA cache_size=-2000")  # 2MB cache
        conn.execute("PRAGMA busy_timeout=5000")  # Wait up to 5s on locks
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA foreign_keys=OFF")

        conn.row_factory = sqlite3.Row

        conn.execute(__Q_CREATE_TABLE)
        conn.commit()
        thread_local.conn = conn

    return thread_local.conn


def save_future(
    future: SyftFuture, namespace: str, client: Optional[Client] = None
) -> str:
    client = client or get_default_client()
    conn = __get_connection(client)
    data = future.model_dump(mode="json")

    conn.execute(__Q_INSERT_FUTURE, {**data, "namespace": namespace})
    conn.commit()

    return data["id"]


def get_future(
    future_id: Union[UUID, str], client: Optional[Client] = None
) -> Optional[SyftFuture]:
    client = client or get_default_client()
    conn = __get_connection(client)
    row = conn.execute(
        "SELECT * FROM futures WHERE id = ?", (str(future_id),)
    ).fetchone()

    if not row:
        return None

    return SyftFuture(**dict(row))


def delete_future(future_id: Union[UUID, str], client: Optional[Client] = None) -> None:
    client = client or get_default_client()
    conn = __get_connection(client)
    conn.execute("DELETE FROM futures WHERE id = ?", (str(future_id),))
    conn.commit()


def cleanup_expired_futures(client: Optional[Client] = None) -> None:
    client = client or Client.load()
    conn = __get_connection(client)
    conn.execute("DELETE FROM futures WHERE expires < datetime('now')")
    conn.commit()


def list_futures(namespace: Optional[str] = None, client: Optional[Client] = None):
    client = client or Client.load()
    conn = __get_connection(client)
    query_all = "SELECT id, path, expires FROM futures"
    query_app = "SELECT id, path, expires FROM futures WHERE namespace = ?"

    if namespace:
        rows = conn.execute(query_app, (namespace,)).fetchall()
    else:
        rows = conn.execute(query_all).fetchall()
    return [SyftFuture(**dict(row)) for row in rows]
