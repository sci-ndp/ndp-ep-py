"""Record of which Pelican events have already been handed to the caller.

Internal module: the public interface is `APIClient.subscribe_pelican`.

Delivery is at-least-once. The event server resends anything it did not
see acknowledged, and a client that restarts resumes wherever the server
left off, so the same event can arrive more than once. Consumers want it
once, which is what this table provides. Keeping it on disk rather than
in memory is what makes a subscription survive a restart without
reprocessing its backlog.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_events (
    client_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    destination TEXT NOT NULL,
    body TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    PRIMARY KEY (client_id, event_id)
)
"""


class EventStore:
    """Durable set of event identities already seen by one client."""

    def __init__(self, path: Union[str, Path], client_id: str) -> None:
        """
        Open, creating the database and its parent directory if needed.

        Args:
            path: Location of the SQLite file.
            client_id: Scopes the records, so several clients can share
                one file without seeing each other's history.
        """
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.client_id = client_id

        # The reader is the caller's thread while the writer is the
        # subscription's; SQLite objects are not safe to share across
        # threads without both of these.
        self._lock = threading.Lock()
        self._closed = False
        self._final_count = 0
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        with self._db:
            self._db.execute(_SCHEMA)

    def record(self, event_id: str, destination: str, body: str) -> bool:
        """
        Record an event.

        Returns:
            True the first time this event is seen, False on redelivery.
        """
        with self._lock, self._db:
            cursor = self._db.execute(
                "INSERT OR IGNORE INTO processed_events "
                "(client_id, event_id, destination, body, processed_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    self.client_id,
                    event_id,
                    destination,
                    body,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return bool(cursor.rowcount)

    def seen(self, event_id: str) -> bool:
        """Report whether an event has already been recorded."""
        with self._lock:
            row = self._db.execute(
                "SELECT 1 FROM processed_events "
                "WHERE client_id = ? AND event_id = ?",
                (self.client_id, event_id),
            ).fetchone()
        return row is not None

    @property
    def processed_count(self) -> int:
        """Number of distinct events recorded for this client.

        Still answerable after `close`, which is when a caller is most
        likely to ask: reporting a subscription's totals is the natural
        last thing to do with it.
        """
        with self._lock:
            if self._closed:
                return self._final_count
            row = self._db.execute(
                "SELECT COUNT(*) FROM processed_events WHERE client_id = ?",
                (self.client_id,),
            ).fetchone()
        return int(row[0])

    @property
    def closed(self) -> bool:
        """Whether the database has been closed."""
        return self._closed

    def close(self) -> None:
        """Close the database, keeping the final count readable."""
        with self._lock:
            if self._closed:
                return
            row = self._db.execute(
                "SELECT COUNT(*) FROM processed_events WHERE client_id = ?",
                (self.client_id,),
            ).fetchone()
            self._final_count = int(row[0])
            self._db.close()
            self._closed = True
