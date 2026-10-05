"""Subscribe to Pelican file events.

The event server notifies subscribers whenever an object appears in a
Pelican namespace. `subscribe_pelican` turns that into an ordinary
Python iterator of `PelicanEvent`, so the caller never has to deal with
STOMP, WebSockets or asyncio:

    with client.subscribe_pelican("osdf/vdc/public/data", "my-client") as s:
        for event in s:
            data = client.pelican_read(event.url)

The connection runs on its own thread and event loop, which is what lets
the same code work in a script and in a notebook that already has a
running loop.

Requires the optional dependencies behind the ``[pelican]`` extra::

    pip install ndp-ep[pelican]
"""

from __future__ import annotations

import asyncio
import base64
import inspect
import logging
import queue
import threading
import warnings
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Union

from ._event_store import EventStore
from ._pelican_protocol import (
    Frame,
    PelicanEvent,
    event_identity,
    is_heartbeat,
    parse_file_event,
    parse_frame,
    websocket_url,
)
from .client_base import APIClientBase

try:
    import websockets
except ImportError:  # pragma: no cover - optional dependency at runtime
    websockets = None

logger = logging.getLogger(__name__)

#: Event server. Fixed for now; a future release should learn it from
#: the Endpoint's status route rather than hard-coding it.
DEFAULT_EVENT_SERVER = "https://stomp-server.chtcdev.chtc.io/ws"

DEFAULT_HEARTBEAT_MS = 10000
DEFAULT_STATE_DB = "~/.ndp_ep/pelican_events.sqlite3"
DEFAULT_VIRTUAL_HOST = "playground"

_MAX_BACKOFF_SECONDS = 30
_SENTINEL = object()

_credentials_warned = False


def _basic_auth(username: str, password: str) -> str:
    raw = f"{username}:{password}".encode()
    return f"Basic {base64.b64encode(raw).decode()}"


def _header_kwargs(headers: Optional[Dict[str, str]]) -> Dict[str, Any]:
    """Name the handshake-header argument the way this websockets wants it."""
    if headers is None:
        return {}
    parameters = inspect.signature(websockets.connect).parameters
    if "additional_headers" in parameters:
        return {"additional_headers": headers}
    return {"extra_headers": headers}


def _warn_about_credentials() -> None:
    global _credentials_warned
    if _credentials_warned:
        return
    _credentials_warned = True
    warnings.warn(
        "Pelican event subscriptions authenticate with a username and "
        "password held by the event server. This is a temporary "
        "arrangement and will be replaced by an access token; expect "
        "these arguments to change.",
        FutureWarning,
        stacklevel=3,
    )


class PelicanSubscription:
    """A live subscription to a Pelican namespace.

    Iterating yields each event once, in arrival order, blocking until
    the next one arrives. Use it as a context manager, or call `close()`,
    so the connection and the state database are released.

    Redeliveries are suppressed using a record on disk, so restarting a
    program does not reprocess events it already handed out. The flip
    side is that an event is considered delivered once it has been queued
    for the caller: if the process dies between that point and the
    caller acting on it, that event will not come round again.
    """

    def __init__(
        self,
        event_source: str,
        client_id: str,
        *,
        subscription: Optional[str] = None,
        username: str = "",
        password: str = "",
        url: str = DEFAULT_EVENT_SERVER,
        state_db: Union[str, Path] = DEFAULT_STATE_DB,
        heartbeat: int = DEFAULT_HEARTBEAT_MS,
        reconnect: bool = True,
        virtual_host: str = DEFAULT_VIRTUAL_HOST,
    ) -> None:
        if websockets is None:  # pragma: no cover - optional install
            raise ValueError(
                "websockets is not installed. Install it with "
                "'pip install ndp-ep[pelican]' to subscribe to Pelican "
                "events."
            )

        if not event_source or not event_source.strip():
            raise ValueError("event_source must be a non-empty string.")
        if not client_id or not client_id.strip():
            raise ValueError("client_id must be a non-empty string.")
        if bool(username) != bool(password):
            raise ValueError(
                "username and password must be provided together."
            )
        if heartbeat < 1000:
            raise ValueError("heartbeat must be at least 1000 milliseconds.")

        self.event_source = event_source.strip().strip("/")
        self.client_id = client_id.strip()
        self.subscription = (subscription or self.client_id).strip()
        # The subscription is one segment of the destination, so a slash
        # in it would silently reroute the subscription. The event source
        # is the remainder of the path and may contain slashes.
        if "/" in self.subscription:
            raise ValueError("subscription must not contain '/'.")

        self.url = websocket_url(url)
        self.username = username
        self.password = password
        self.heartbeat = heartbeat
        self.reconnect = reconnect
        self.virtual_host = virtual_host

        if username:
            _warn_about_credentials()

        self._store = EventStore(state_db, self.client_id)
        # Unbounded on purpose: a bounded buffer would silently drop the
        # oldest events whenever the consumer falls behind the publisher.
        self._queue: "queue.Queue[Any]" = queue.Queue()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[Any] = None
        self._connection: Optional[Any] = None

        self.state = "starting"
        self.last_error = ""
        self.session: Dict[str, str] = {}
        self.subscription_active = False
        self.metrics = {
            "connection_attempts": 0,
            "sessions_established": 0,
            "connection_failures": 0,
            "messages_received": 0,
            "events_delivered": 0,
            "duplicates_suppressed": 0,
            "unparseable_messages": 0,
            "server_errors": 0,
            "acks_sent": 0,
        }

    # -- public interface -------------------------------------------------

    @property
    def destination(self) -> str:
        """The STOMP destination this subscription listens on."""
        return f"{self.subscription}/{self.event_source}"

    def start(self) -> "PelicanSubscription":
        """Open the connection and begin receiving, without blocking."""
        if self._thread is not None:
            raise RuntimeError("This subscription has already been started.")
        self._thread = threading.Thread(
            target=self._thread_main,
            name=f"pelican-events-{self.client_id}",
            daemon=True,
        )
        self._thread.start()
        return self

    def wait_until_connected(self, timeout: float = 20.0) -> bool:
        """
        Block until the subscription is active, or the timeout expires.

        Returns:
            True if the subscription became active in time.
        """
        deadline = threading.Event()
        step = 0.1
        waited = 0.0
        while waited < timeout:
            if self.subscription_active:
                return True
            if self._thread is not None and not self._thread.is_alive():
                return False
            deadline.wait(step)
            waited += step
        return self.subscription_active

    def events(
        self, timeout: Optional[float] = None
    ) -> Iterator[PelicanEvent]:
        """
        Yield events as they arrive, each exactly once.

        Args:
            timeout: Seconds to wait for the next event before stopping.
                None waits indefinitely.
        """
        while True:
            try:
                item = self._queue.get(timeout=timeout)
            except queue.Empty:
                return
            if item is _SENTINEL:
                # Put it back so any other reader also stops.
                self._queue.put(_SENTINEL)
                return
            yield item

    def __iter__(self) -> Iterator[PelicanEvent]:
        return self.events()

    def close(self, timeout: float = 5.0) -> None:
        """Stop receiving and release the connection and the database.

        The WebSocket is closed with its handshake rather than dropped:
        cancelling the task outright leaves the event server holding a
        half-open connection until its own keepalive notices.
        """
        self._stop.set()
        loop = self._loop

        # Ask the loop to close the connection, then wait on the thread
        # rather than on that coroutine: the loop shuts down as soon as
        # the receive task unwinds, which can abandon a coroutine still
        # being awaited from here.
        if loop is not None and not loop.is_closed():
            loop.call_soon_threadsafe(self._begin_shutdown)

        if self._thread is not None:
            self._thread.join(timeout)
            if self._thread.is_alive():  # pragma: no cover - stuck session
                task = self._task
                if loop is not None and not loop.is_closed() and task:
                    loop.call_soon_threadsafe(task.cancel)
                self._thread.join(timeout)

        self._queue.put(_SENTINEL)
        self._store.close()
        self.state = "closed"
        self.subscription_active = False

    def __enter__(self) -> "PelicanSubscription":
        if self._thread is None:
            self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    @property
    def status(self) -> Dict[str, Any]:
        """A snapshot of connection state, useful when something is wrong."""
        return {
            "state": self.state,
            "last_error": self.last_error,
            "session": dict(self.session),
            "subscription": {
                "id": self.subscription,
                "destination": self.destination,
                "active": self.subscription_active,
            },
            "config": {
                "url": self.url,
                "event_source": self.event_source,
                "client_id": self.client_id,
                "heartbeat": self.heartbeat,
                "reconnect": self.reconnect,
                "authenticated": bool(self.username),
            },
            "metrics": dict(self.metrics),
            "pending": self._queue.qsize(),
            "processed_total": self._store.processed_count,
        }

    # -- connection -------------------------------------------------------

    def _begin_shutdown(self) -> None:
        """Start closing the connection. Runs on the subscription's loop."""
        if self._connection is not None:
            asyncio.ensure_future(self._shutdown())

    async def _shutdown(self) -> None:
        """Close the live connection, letting the receive loop unwind."""
        connection = self._connection
        if connection is not None:
            try:
                await connection.close()
            except Exception:  # pragma: no cover - best-effort shutdown
                logger.debug("Closing the connection failed", exc_info=True)

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            self._task = loop.create_task(self._run())
            loop.run_until_complete(self._task)
        except asyncio.CancelledError:  # pragma: no cover - shutdown path
            pass
        finally:
            try:
                # Let the closing handshake finish before the loop goes.
                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                if pending:
                    loop.run_until_complete(asyncio.wait(pending, timeout=2))
            except Exception:  # pragma: no cover - best-effort shutdown
                logger.debug("Draining the loop failed", exc_info=True)
            try:
                loop.close()
            finally:
                self.state = "disconnected"
                self._queue.put(_SENTINEL)

    async def _run(self) -> None:
        delay = 1.0
        while not self._stop.is_set():
            try:
                await self._session()
                delay = 1.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if self._stop.is_set():
                    return
                self.metrics["connection_failures"] += 1
                self.state = "error"
                self.last_error = f"{type(exc).__name__}: {exc}"
                if not self.reconnect:
                    logger.warning(
                        "Pelican event connection failed and reconnect is "
                        "off: %s",
                        self.last_error,
                    )
                    return
                logger.warning(
                    "Pelican event connection failed (%s); retrying in %.0fs",
                    self.last_error,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, _MAX_BACKOFF_SECONDS)

    async def _session(self) -> None:
        self.metrics["connection_attempts"] += 1
        self.state = "connecting"
        self.last_error = ""

        headers = None
        if self.username:
            headers = {
                "Authorization": _basic_auth(self.username, self.password)
            }

        # The heartbeat below is our own liveness signal, so the library's
        # keepalive would only duplicate it.
        connect = websockets.connect(
            self.url, ping_interval=None, **_header_kwargs(headers)
        )
        async with connect as connection:
            self._connection = connection
            await self._send(connection, self._connect_frame())

            greeting = await self._receive(connection)
            if greeting.command != "CONNECTED":
                raise RuntimeError(
                    f"Expected CONNECTED from the event server, got "
                    f"{greeting.command or 'nothing'}."
                )

            self.session = greeting.headers
            self.metrics["sessions_established"] += 1
            self.state = "connected"

            await self._send(connection, self._subscribe_frame())
            self.subscription_active = True
            logger.info(
                "Subscribed to %s as %s", self.destination, self.client_id
            )

            heartbeat = asyncio.ensure_future(self._heartbeat(connection))
            try:
                while not self._stop.is_set():
                    frame = await self._receive(connection)
                    if frame.command == "MESSAGE":
                        await self._on_message(connection, frame)
                    elif frame.command == "ERROR":
                        self._on_server_error(frame)
            finally:
                heartbeat.cancel()
                self.subscription_active = False
                self._connection = None

    def _connect_frame(self) -> Frame:
        return Frame(
            "CONNECT",
            {
                "accept-version": "1.2",
                "host": self.virtual_host,
                "client-id": self.client_id,
                "heart-beat": f"{self.heartbeat},{self.heartbeat}",
            },
        )

    def _subscribe_frame(self) -> Frame:
        return Frame(
            "SUBSCRIBE",
            {
                "id": self.subscription,
                "subscription": self.subscription,
                "destination": self.destination,
                "ack": "client-individual",
            },
        )

    async def _heartbeat(self, connection: Any) -> None:
        """Send the heartbeats promised in CONNECT.

        Sent at half the negotiated interval so an ordinary scheduling
        delay is not read by the server as a dead client.
        """
        interval = self.heartbeat / 2000
        while True:
            await asyncio.sleep(interval)
            await connection.send(b"\n")

    async def _send(self, connection: Any, frame: Frame) -> None:
        await connection.send(frame.encode())
        logger.debug("-> %s %s", frame.command, frame.headers)

    async def _receive(self, connection: Any) -> Frame:
        data = await connection.recv()
        if isinstance(data, str):
            data = data.encode()
        if is_heartbeat(data):
            return Frame("HEARTBEAT")
        frame = parse_frame(data)
        logger.debug("<- %s %s", frame.command, frame.headers)
        return frame

    async def _on_message(self, connection: Any, frame: Frame) -> None:
        self.metrics["messages_received"] += 1
        destination = frame.headers.get("destination", "")
        identity = event_identity(frame)

        if self._store.record(identity, destination, frame.body):
            try:
                event = parse_file_event(frame.body, identity, destination)
            except ValueError as exc:
                self.metrics["unparseable_messages"] += 1
                logger.warning("Ignoring unreadable event: %s", exc)
            else:
                self._queue.put(event)
                self.metrics["events_delivered"] += 1
        else:
            self.metrics["duplicates_suppressed"] += 1
            logger.debug("Suppressed redelivery of %s", identity)

        ack_id = frame.headers.get("ack")
        if ack_id:
            await self._send(connection, Frame("ACK", {"id": ack_id}))
            self.metrics["acks_sent"] += 1

    def _on_server_error(self, frame: Frame) -> None:
        message = frame.body or frame.headers.get("message", "server error")
        self.metrics["server_errors"] += 1
        self.last_error = f"Server error: {message}"
        logger.error("Event server reported an error: %s", message)


class APIClientPelicanEvents(APIClientBase):
    """Extension of APIClientBase with Pelican event subscriptions."""

    def subscribe_pelican(
        self,
        event_source: str,
        client_id: str,
        *,
        subscription: Optional[str] = None,
        username: str = "",
        password: str = "",
        url: str = DEFAULT_EVENT_SERVER,
        state_db: Union[str, Path] = DEFAULT_STATE_DB,
        heartbeat: int = DEFAULT_HEARTBEAT_MS,
        reconnect: bool = True,
        start: bool = True,
    ) -> PelicanSubscription:
        """
        Subscribe to file events for a Pelican namespace.

        Args:
            event_source: Namespace to watch, for example
                "osdf/vdc/public/pelican_protocol".
            client_id: Identifies this subscriber. Must be unique: two
                clients sharing an id compete for the same events.
            subscription: Routing key, defaulting to `client_id`. Must
                not contain "/".
            username: Event server username. Temporary, see below.
            password: Event server password. Temporary, see below.
            url: Event server URL.
            state_db: Where to record delivered events, so that a
                restart does not reprocess them.
            heartbeat: Liveness interval in milliseconds.
            reconnect: Reconnect with backoff after a dropped
                connection. When False, the iterator ends instead.
            start: Connect immediately. When False, call `start()` or
                use the subscription as a context manager.

        Returns:
            A `PelicanSubscription`, which iterates as events arrive.

        Raises:
            ValueError: If the optional dependencies are missing or an
                argument is unusable.

        Note:
            Credentials are checked by the event server against its own
            store; they are unrelated to the Endpoint token this client
            holds. They will be replaced by an access token once the
            event server trusts tokens issued for NDP.

        Example:
            >>> with client.subscribe_pelican(
            ...     "osdf/vdc/public/pelican_protocol",
            ...     client_id="my-client",
            ...     username="user",
            ...     password="secret",
            ... ) as subscription:
            ...     for event in subscription:
            ...         print(event.name, event.size)
            ...         raw = client.pelican_read(event.url)
        """
        subscriber = PelicanSubscription(
            event_source,
            client_id,
            subscription=subscription,
            username=username,
            password=password,
            url=url,
            state_db=state_db,
            heartbeat=heartbeat,
            reconnect=reconnect,
        )
        if start:
            subscriber.start()
        return subscriber
