"""Tests for Pelican file-event subscriptions.

The connection tests run against a real WebSocket server on localhost
that speaks the same STOMP exchange as the event server, so the frames
this client sends are actually parsed by something rather than compared
to an expected string.
"""

import asyncio
import base64
import json
import threading
import time

import pytest
import requests_mock
import websockets

from ndp_ep._pelican_protocol import Frame, parse_frame
from ndp_ep.pelican_events_method import (
    APIClientPelicanEvents,
    PelicanSubscription,
)


def event_body(index, uuid=None):
    """Build an event body for the fake publisher."""
    return json.dumps(
        {
            "name": f"file_{index}.csv",
            "url": f"osdf://vdc/public/data/file_{index}.csv",
            "size": 100 + index,
            "mod_time": "2026-08-21T09:00:00Z",
            "uuid": uuid or f"uuid-{index}",
        }
    )


class FakeEventServer:
    """A localhost stand-in for the Pelican event server."""

    def __init__(
        self,
        bodies,
        require_auth=True,
        wrap_in_json_string=False,
        close_after_publish=False,
    ):
        self.bodies = bodies
        self.require_auth = require_auth
        self.wrap_in_json_string = wrap_in_json_string
        self.close_after_publish = close_after_publish
        self.open_connections = set()
        self.connect_frames = []
        self.subscribe_frames = []
        self.acks = []
        self.heartbeats = 0
        self.authorization = None
        self.connections = 0
        self.port = None
        self._loop = None
        self._thread = None
        self._ready = threading.Event()
        self._stop = None

    # -- lifecycle --------------------------------------------------------

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        assert self._ready.wait(10), "fake event server did not start"
        return self

    def stop(self):
        if self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread is not None:
            self._thread.join(5)

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._stop = asyncio.Event()
        try:
            loop.run_until_complete(self._serve())
        finally:
            loop.close()

    async def _serve(self):
        async with websockets.serve(self._handle, "127.0.0.1", 0) as server:
            self.port = list(server.sockets)[0].getsockname()[1]
            self._ready.set()
            await self._stop.wait()
            # Leaving the context waits for live handlers, and they are
            # parked on recv(); close them or shutdown blocks.
            for connection in list(self.open_connections):
                await connection.close()

    # -- protocol ---------------------------------------------------------

    async def _handle(self, connection):
        self.connections += 1
        self.open_connections.add(connection)
        try:
            await self._exchange(connection)
        finally:
            self.open_connections.discard(connection)

    async def _exchange(self, connection):
        request = getattr(connection, "request", None)
        if request is not None:
            self.authorization = request.headers.get("Authorization")
        if self.require_auth and not self.authorization:
            await connection.close(code=4401, reason="unauthorized")
            return

        connect = await self._recv(connection)
        self.connect_frames.append(connect)
        await self._send(
            connection,
            Frame(
                "CONNECTED",
                {
                    "version": "1.2",
                    "server": "fake-event-server",
                    "session": "session-1",
                },
            ),
        )

        subscribe = await self._recv(connection)
        self.subscribe_frames.append(subscribe)
        destination = subscribe.headers.get("destination", "")

        for index, body in enumerate(self.bodies):
            if self.wrap_in_json_string:
                body = json.dumps(body)
            await self._send(
                connection,
                Frame(
                    "MESSAGE",
                    {
                        "destination": destination,
                        "message-id": f"server-{index}",
                        "subscription": subscribe.headers.get("id", ""),
                        "ack": f"ack-{index}",
                    },
                    body,
                ),
            )

        if self.close_after_publish:
            await connection.close(code=4000, reason="session ended")
            return

        # Stay open so the client can send its ACKs and heartbeats.
        try:
            while True:
                frame = await self._recv(connection)
                if frame.command == "ACK":
                    self.acks.append(frame.headers.get("id"))
                elif frame.command == "HEARTBEAT":
                    self.heartbeats += 1
        except websockets.exceptions.ConnectionClosed:
            return

    async def _send(self, connection, frame):
        await connection.send(frame.encode())

    async def _recv(self, connection):
        data = await connection.recv()
        if isinstance(data, str):
            data = data.encode()
        if data in (b"\n", b"\r\n"):
            return Frame("HEARTBEAT")
        return parse_frame(data)


@pytest.fixture
def server():
    """Run a fake event server publishing three events."""
    fake = FakeEventServer([event_body(i) for i in range(3)]).start()
    yield fake
    fake.stop()


@pytest.fixture
def client():
    """Create a client for the event subscription mixin."""
    with requests_mock.Mocker() as m:
        m.get("http://example.com", status_code=200)
        return APIClientPelicanEvents(base_url="http://example.com")


def subscribe(server, tmp_path, **overrides):
    """Build a subscription pointed at the fake server."""
    options = {
        "event_source": "osdf/vdc/public/data",
        "client_id": "test-client",
        "username": "user",
        "password": "secret",
        "url": f"http://127.0.0.1:{server.port}",
        "state_db": tmp_path / "events.sqlite3",
    }
    options.update(overrides)
    return PelicanSubscription(**options)


def collect(subscription, count, timeout=10.0):
    """Take up to `count` events, giving up after `timeout`."""
    events = []
    deadline = time.monotonic() + timeout
    for event in subscription.events(timeout=timeout):
        events.append(event)
        if len(events) >= count or time.monotonic() > deadline:
            break
    return events


class TestValidation:
    """Arguments are checked before any connection is attempted."""

    @pytest.mark.parametrize(
        "overrides,message",
        [
            ({"event_source": ""}, "event_source"),
            ({"event_source": "   "}, "event_source"),
            ({"client_id": ""}, "client_id"),
            ({"subscription": "has/slash"}, "must not contain"),
            ({"heartbeat": 500}, "at least 1000"),
            ({"password": ""}, "provided together"),
            ({"url": "ftp://nope"}, "http\\(s\\) or ws\\(s\\)"),
        ],
    )
    def test_rejected(self, tmp_path, overrides, message):
        """Each unusable argument is rejected with a clear message."""
        options = {
            "event_source": "osdf/vdc/public/data",
            "client_id": "test-client",
            "username": "user",
            "password": "secret",
            "url": "http://127.0.0.1:1",
            "state_db": tmp_path / "events.sqlite3",
        }
        options.update(overrides)

        with pytest.raises(ValueError, match=message):
            PelicanSubscription(**options)

    def test_destination_composition(self, tmp_path):
        """The destination is the subscription joined to the source."""
        subscription = PelicanSubscription(
            "osdf/vdc/public/data",
            "test-client",
            url="http://127.0.0.1:1",
            state_db=tmp_path / "events.sqlite3",
        )

        assert subscription.destination == ("test-client/osdf/vdc/public/data")

    def test_subscription_defaults_to_client_id(self, tmp_path):
        """Without an explicit routing key the client id is used."""
        subscription = PelicanSubscription(
            "osdf/vdc/public/data",
            "test-client",
            url="http://127.0.0.1:1",
            state_db=tmp_path / "events.sqlite3",
        )

        assert subscription.subscription == "test-client"

    def test_explicit_subscription_is_used(self, tmp_path):
        """An explicit routing key overrides the client id."""
        subscription = PelicanSubscription(
            "osdf/vdc/public/data",
            "test-client",
            subscription="shared-key",
            url="http://127.0.0.1:1",
            state_db=tmp_path / "events.sqlite3",
        )

        assert subscription.destination == "shared-key/osdf/vdc/public/data"

    def test_source_slashes_are_trimmed_not_rejected(self, tmp_path):
        """Slashes belong in the event source and are tolerated."""
        subscription = PelicanSubscription(
            "/osdf/vdc/public/data/",
            "test-client",
            url="http://127.0.0.1:1",
            state_db=tmp_path / "events.sqlite3",
        )

        assert subscription.event_source == "osdf/vdc/public/data"

    def test_credentials_warn_once(self, tmp_path, monkeypatch):
        """Password auth announces that it is temporary."""
        monkeypatch.setattr(
            "ndp_ep.pelican_events_method._credentials_warned", False
        )

        with pytest.warns(FutureWarning, match="access token"):
            PelicanSubscription(
                "osdf/vdc/public/data",
                "test-client",
                username="user",
                password="secret",
                url="http://127.0.0.1:1",
                state_db=tmp_path / "events.sqlite3",
            )


class TestSubscription:
    """The exchange with the event server."""

    def test_receives_events(self, server, tmp_path):
        """Published events reach the caller as an iterator."""
        with subscribe(server, tmp_path) as subscription:
            events = collect(subscription, 3)

        assert [event.name for event in events] == [
            "file_0.csv",
            "file_1.csv",
            "file_2.csv",
        ]
        assert events[0].size == 100
        assert events[0].url.endswith("file_0.csv")

    def test_sends_basic_auth(self, server, tmp_path):
        """Credentials travel as Basic auth on the handshake."""
        with subscribe(server, tmp_path) as subscription:
            collect(subscription, 3)

        expected = base64.b64encode(b"user:secret").decode()
        assert server.authorization == f"Basic {expected}"

    def test_connect_frame_contents(self, server, tmp_path):
        """CONNECT announces the version, client and heartbeat."""
        with subscribe(server, tmp_path) as subscription:
            collect(subscription, 3)

        headers = server.connect_frames[0].headers
        assert headers["accept-version"] == "1.2"
        assert headers["client-id"] == "test-client"
        assert headers["heart-beat"] == "10000,10000"

    def test_subscribe_frame_contents(self, server, tmp_path):
        """SUBSCRIBE asks for individual acknowledgement."""
        with subscribe(server, tmp_path) as subscription:
            collect(subscription, 3)

        headers = server.subscribe_frames[0].headers
        assert headers["destination"] == "test-client/osdf/vdc/public/data"
        assert headers["id"] == "test-client"
        assert headers["ack"] == "client-individual"

    def test_acknowledges_every_message(self, server, tmp_path):
        """Each delivered message is acknowledged by its ack id."""
        with subscribe(server, tmp_path) as subscription:
            collect(subscription, 3)
            deadline = time.monotonic() + 5
            while len(server.acks) < 3 and time.monotonic() < deadline:
                time.sleep(0.05)

        assert server.acks == ["ack-0", "ack-1", "ack-2"]

    def test_json_string_envelope_is_unwrapped(self, tmp_path):
        """Bodies double-encoded as JSON strings are still readable."""
        fake = FakeEventServer(
            [event_body(0)], wrap_in_json_string=True
        ).start()
        try:
            with subscribe(fake, tmp_path) as subscription:
                events = collect(subscription, 1)
        finally:
            fake.stop()

        assert events[0].name == "file_0.csv"

    def test_redeliveries_are_suppressed(self, tmp_path):
        """The same event delivered twice is handed out once."""
        bodies = [event_body(0), event_body(0), event_body(1)]
        fake = FakeEventServer(bodies).start()
        try:
            with subscribe(fake, tmp_path) as subscription:
                events = collect(subscription, 2)
                assert subscription.metrics["duplicates_suppressed"] == 1
        finally:
            fake.stop()

        assert [event.name for event in events] == [
            "file_0.csv",
            "file_1.csv",
        ]

    def test_duplicates_are_still_acknowledged(self, tmp_path):
        """A suppressed redelivery is acknowledged, or it repeats."""
        fake = FakeEventServer([event_body(0), event_body(0)]).start()
        try:
            with subscribe(fake, tmp_path) as subscription:
                collect(subscription, 1)
                deadline = time.monotonic() + 5
                while len(fake.acks) < 2 and time.monotonic() < deadline:
                    time.sleep(0.05)
        finally:
            fake.stop()

        assert fake.acks == ["ack-0", "ack-1"]

    def test_restart_does_not_replay(self, server, tmp_path):
        """A new subscription sharing the database skips old events."""
        state = tmp_path / "events.sqlite3"
        with subscribe(server, tmp_path, state_db=state) as first:
            collect(first, 3)

        with subscribe(server, tmp_path, state_db=state) as second:
            replayed = collect(second, 1, timeout=2.0)

        assert replayed == []
        assert second.metrics["duplicates_suppressed"] == 3

    def test_unreadable_events_are_skipped(self, tmp_path):
        """A malformed body is dropped without stopping the stream."""
        fake = FakeEventServer(["not json at all", event_body(1)]).start()
        try:
            with subscribe(fake, tmp_path) as subscription:
                events = collect(subscription, 1)
                assert subscription.metrics["unparseable_messages"] == 1
        finally:
            fake.stop()

        assert [event.name for event in events] == ["file_1.csv"]

    def test_status_reports_the_session(self, server, tmp_path):
        """Status exposes enough to diagnose a live subscription."""
        with subscribe(server, tmp_path) as subscription:
            collect(subscription, 3)
            status = subscription.status

        assert status["state"] == "connected"
        assert status["subscription"]["active"] is True
        assert status["subscription"]["destination"] == (
            "test-client/osdf/vdc/public/data"
        )
        assert status["session"]["server"] == "fake-event-server"
        assert status["config"]["authenticated"] is True
        assert status["metrics"]["events_delivered"] == 3
        assert status["processed_total"] == 3

    def test_wait_until_connected(self, server, tmp_path):
        """The helper reports once the subscription is active."""
        with subscribe(server, tmp_path) as subscription:
            assert subscription.wait_until_connected(timeout=10) is True

    def test_close_is_idempotent(self, server, tmp_path):
        """Closing twice does not raise."""
        subscription = subscribe(server, tmp_path).start()
        subscription.wait_until_connected(timeout=10)
        subscription.close()
        subscription.close()

        assert subscription.state == "closed"

    def test_cannot_start_twice(self, server, tmp_path):
        """Starting an already running subscription is an error."""
        with subscribe(server, tmp_path) as subscription:
            with pytest.raises(RuntimeError, match="already been started"):
                subscription.start()

    def test_iteration_ends_after_close(self, server, tmp_path):
        """Closing releases a blocked iterator."""
        subscription = subscribe(server, tmp_path).start()
        collect(subscription, 3)
        subscription.close()

        assert list(subscription.events(timeout=2.0)) == []

    def test_without_reconnect_iteration_ends(self, tmp_path):
        """A refused connection ends the stream when reconnect is off."""
        subscription = PelicanSubscription(
            "osdf/vdc/public/data",
            "test-client",
            url="http://127.0.0.1:9",
            state_db=tmp_path / "events.sqlite3",
            reconnect=False,
        )
        subscription.start()
        try:
            assert list(subscription.events(timeout=10.0)) == []
            assert subscription.metrics["connection_failures"] == 1
            assert subscription.last_error != ""
        finally:
            subscription.close()

    def test_reconnects_after_a_dropped_connection(self, tmp_path):
        """A server that hangs up is reconnected to, and events resume.

        The server closes the socket right after publishing, so surviving
        the drop is the only way the second event can arrive.
        """
        fake = FakeEventServer(
            [event_body(0)], close_after_publish=True
        ).start()
        try:
            with subscribe(fake, tmp_path) as subscription:
                first = collect(subscription, 1)
                fake.bodies = [event_body(1)]
                second = collect(subscription, 1, timeout=15.0)

                assert fake.connections >= 2
                assert subscription.metrics["sessions_established"] >= 2
        finally:
            fake.stop()

        assert [event.name for event in first] == ["file_0.csv"]
        assert [event.name for event in second] == ["file_1.csv"]


class TestMixin:
    """The client method that builds a subscription."""

    def test_subscribe_pelican_returns_a_started_subscription(
        self, client, server, tmp_path
    ):
        """The mixin connects by default."""
        subscription = client.subscribe_pelican(
            "osdf/vdc/public/data",
            "test-client",
            username="user",
            password="secret",
            url=f"http://127.0.0.1:{server.port}",
            state_db=tmp_path / "events.sqlite3",
        )
        try:
            assert subscription.wait_until_connected(timeout=10) is True
            assert [e.name for e in collect(subscription, 3)] == [
                "file_0.csv",
                "file_1.csv",
                "file_2.csv",
            ]
        finally:
            subscription.close()

    def test_start_false_does_not_connect(self, client, server, tmp_path):
        """With start=False nothing happens until the caller asks."""
        subscription = client.subscribe_pelican(
            "osdf/vdc/public/data",
            "test-client",
            username="user",
            password="secret",
            url=f"http://127.0.0.1:{server.port}",
            state_db=tmp_path / "events.sqlite3",
            start=False,
        )

        assert subscription.state == "starting"
        assert server.connections == 0

        with subscription:
            assert subscription.wait_until_connected(timeout=10) is True
