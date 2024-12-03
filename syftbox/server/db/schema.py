
# @contextlib.contextmanager
def get_db(path: str):
    conn = sqlite3.connect(path, check_same_thread=False)

    with conn:
        conn.execute("PRAGMA cache_size=10000;")
        conn.execute("PRAGMA synchronous=OFF;")
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        # Create the table if it doesn't exist
        conn.execute("""
        CREATE TABLE IF NOT EXISTS file_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            signature TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            last_modified TEXT NOT NULL        )
        """)
    return conn



# TODO: migrate file_metadata id?
# TODO: think about migrations

import sqlite3
connection = sqlite3.connect(":memory:")
connection.row_factory = sqlite3.Row  # Set row factory to sqlite3.Row
# connection.row_factory = sqlite3.Row  # Set row factory to sqlite3.Row


# Create a cursor object
cursor = connection.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

# Create a table for storing file information
res = cursor.execute("""
    CREATE TABLE rules (
        permfile_path varchar(1000) NOT NULL,
        permfile_dir varchar(1000) NOT NULL,
        priority INTEGER NOT NULL,
        path varchar(1000) NOT NULL,
        user varchar(1000) NOT NULL,
        can_read bool NOT NULL,
        can_create bool NOT NULL,
        can_write bool NOT NULL,
        admin bool NOT NULL,
        disallow bool NOT NULL,
        terminal bool not null,
        PRIMARY KEY (permfile_path, priority)
    )
""")





cursor.execute("""
CREATE TABLE rule_files (
    permfile_path varchar(1000) NOT NULL,
    priority INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    match_for_email varchar(1000),
    PRIMARY KEY (permfile_path, priority, file_id),
    FOREIGN KEY (permfile_path, priority) REFERENCES rules(permfile_path, priority) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES file_metadata(id) ON DELETE CASCADE
);
""")
