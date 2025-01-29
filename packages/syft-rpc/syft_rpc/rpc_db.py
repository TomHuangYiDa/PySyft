import sqlite3
from functools import lru_cache
from typing import Optional

from syft_core.client_shim import Client
from ulid import ULID

from syft_rpc.protocol import SyftFuture

__Q_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS futures (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    expires TIMESTAMP NOT NULL
) WITHOUT ROWID
"""

__Q_INSERT_FUTURE = """
INSERT OR REPLACE INTO futures (id, path, expires)
VALUES (:id, :path, :expires)
"""

DEFAULT_CLIENT = Client.load()


@lru_cache(typed=True)
def __get_connection(client: Client) -> sqlite3.Connection:
    db_dir = client.workspace.plugins
    db_dir.mkdir(exist_ok=True, parents=True)
    db_path = db_dir / "rpc.futures.sqlite"
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
    return conn


def save_future(future: SyftFuture, client: Client = None) -> str:
    client = client or DEFAULT_CLIENT
    conn = __get_connection(client)
    data = future.model_dump(mode="json")

    conn.execute(__Q_INSERT_FUTURE, data)
    conn.commit()

    return data["id"]


def get_future(future_id: str | ULID, client: Client = None) -> Optional[SyftFuture]:
    client = client or DEFAULT_CLIENT
    conn = __get_connection(client)
    row = conn.execute(
        "SELECT * FROM futures WHERE id = ?", (str(future_id),)
    ).fetchone()

    if not row:
        return None

    return SyftFuture(**dict(row))


def delete_future(future_id: str | ULID, client: Client = None) -> None:
    client = client or DEFAULT_CLIENT
    conn = __get_connection(client)
    conn.execute("DELETE FROM futures WHERE id = ?", (str(future_id),))
    conn.commit()


def cleanup_expired_futures(client: Client = None) -> None:
    client = client or Client.load()
    conn = __get_connection(client)
    conn.execute("DELETE FROM futures WHERE expires < datetime('now')")
    conn.commit()
