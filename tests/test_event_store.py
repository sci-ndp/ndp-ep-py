"""Tests for the record of delivered Pelican events."""

import threading

from ndp_ep._event_store import EventStore


class TestEventStore:
    """Deduplication across redeliveries and restarts."""

    def test_first_record_is_new(self, tmp_path):
        """An unseen event is reported as new."""
        store = EventStore(tmp_path / "events.sqlite3", "client-a")

        assert store.record("e1", "sub/osdf/a", "{}") is True

    def test_second_record_is_a_duplicate(self, tmp_path):
        """The same event is not new the second time."""
        store = EventStore(tmp_path / "events.sqlite3", "client-a")
        store.record("e1", "sub/osdf/a", "{}")

        assert store.record("e1", "sub/osdf/a", "{}") is False

    def test_survives_reopening(self, tmp_path):
        """A restart does not forget what was already delivered."""
        path = tmp_path / "events.sqlite3"
        first = EventStore(path, "client-a")
        first.record("e1", "sub/osdf/a", "{}")
        first.close()

        second = EventStore(path, "client-a")

        assert second.record("e1", "sub/osdf/a", "{}") is False
        assert second.seen("e1") is True

    def test_clients_do_not_collide(self, tmp_path):
        """Two clients sharing a file keep separate histories."""
        path = tmp_path / "events.sqlite3"
        first = EventStore(path, "client-a")
        second = EventStore(path, "client-b")
        first.record("e1", "sub/osdf/a", "{}")

        assert second.record("e1", "sub/osdf/a", "{}") is True
        assert first.processed_count == 1
        assert second.processed_count == 1

    def test_seen_is_false_for_unknown(self, tmp_path):
        """An event never recorded is not reported as seen."""
        store = EventStore(tmp_path / "events.sqlite3", "client-a")

        assert store.seen("nope") is False

    def test_counts_distinct_events(self, tmp_path):
        """Redeliveries do not inflate the count."""
        store = EventStore(tmp_path / "events.sqlite3", "client-a")
        for identity in ("e1", "e2", "e1", "e3"):
            store.record(identity, "sub/osdf/a", "{}")

        assert store.processed_count == 3

    def test_creates_missing_parent_directories(self, tmp_path):
        """The database directory is created if absent."""
        path = tmp_path / "deeply" / "nested" / "events.sqlite3"

        EventStore(path, "client-a").record("e1", "sub/osdf/a", "{}")

        assert path.exists()

    def test_expands_user_home(self, tmp_path, monkeypatch):
        """A path starting with ~ is expanded."""
        monkeypatch.setenv("HOME", str(tmp_path))

        store = EventStore("~/.ndp_ep/events.sqlite3", "client-a")

        assert store.path == tmp_path / ".ndp_ep" / "events.sqlite3"

    def test_concurrent_writers_record_once(self, tmp_path):
        """Exactly one thread wins when several record the same event."""
        store = EventStore(tmp_path / "events.sqlite3", "client-a")
        results = []
        barrier = threading.Barrier(8)

        def record():
            barrier.wait()
            results.append(store.record("same", "sub/osdf/a", "{}"))

        threads = [threading.Thread(target=record) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert results.count(True) == 1
        assert store.processed_count == 1
