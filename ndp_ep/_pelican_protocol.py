"""Wire format for Pelican file-event subscriptions.

Internal module: the public interface is `APIClient.subscribe_pelican`.

This holds the parts of the protocol that need no network and no optional
dependency, so they stay importable and testable everywhere: STOMP 1.2
frame encoding, and the application-level file event carried in a
MESSAGE body.

STOMP itself does not define the body schema. The event server sends a
JSON object with `name`, `url`, `size` and `mod_time`, sometimes wrapped
in a JSON string; both spellings are accepted here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse

# STOMP 1.2 header escaping. Order matters on the way out: the backslash
# substitution has to happen first or it would re-escape the others.
_ESCAPES = (
    ("\\", "\\\\"),
    ("\r", "\\r"),
    ("\n", "\\n"),
    (":", "\\c"),
)
_UNESCAPES = {"\\": "\\", "r": "\r", "n": "\n", "c": ":"}

_WS_SCHEMES = {"http": "ws", "https": "wss", "ws": "ws", "wss": "wss"}


def escape_header(value: str) -> str:
    """Escape a header name or value for transmission."""
    for plain, escaped in _ESCAPES:
        value = value.replace(plain, escaped)
    return value


def unescape_header(value: str) -> str:
    """Reverse `escape_header`.

    Scans left to right rather than substituting repeatedly, so that an
    escaped backslash followed by a letter (``\\\\n``) yields a backslash
    and an "n" instead of being read a second time as a newline.
    """
    out = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            out.append(_UNESCAPES.get(value[index + 1], value[index + 1]))
            index += 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


@dataclass
class Frame:
    """A STOMP frame."""

    command: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""

    def encode(self) -> bytes:
        """Serialise the frame, terminated by the NUL octet."""
        lines = [self.command]
        lines.extend(
            f"{escape_header(key)}:{escape_header(value)}"
            for key, value in self.headers.items()
        )
        return ("\n".join(lines) + "\n\n" + self.body + "\x00").encode()


def parse_frame(raw: bytes) -> Frame:
    """
    Parse a STOMP frame.

    Repeated headers keep the first value, as STOMP 1.2 requires.
    """
    text = raw.rstrip(b"\x00").decode(errors="replace")
    head, _, body = text.partition("\n\n")
    lines = head.split("\n")

    headers: Dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, _, value = line.partition(":")
            headers.setdefault(unescape_header(key), unescape_header(value))

    return Frame(lines[0], headers, body)


def is_heartbeat(raw: bytes) -> bool:
    """Report whether a received payload is a heartbeat rather than a frame."""
    return raw in (b"\n", b"\r\n")


def websocket_url(value: str) -> str:
    """
    Convert an http(s) or ws(s) URL to its WebSocket form.

    Raises:
        ValueError: If the URL has no host or an unusable scheme.
    """
    parsed = urlparse(value)
    if parsed.scheme not in _WS_SCHEMES or not parsed.netloc:
        raise ValueError(
            f"Event server URL must be an http(s) or ws(s) URL, got '{value}'."
        )
    return urlunparse(parsed._replace(scheme=_WS_SCHEMES[parsed.scheme]))


@dataclass(frozen=True)
class PelicanEvent:
    """A notification that an object appeared in a Pelican namespace.

    Attributes:
        name: Object name, without the namespace path.
        url: Reference to the object, ready to pass to `pelican_read`
            or `pelican_fetch`.
        size: Object size in bytes.
        mod_time: Modification time, as reported by the event server.
        event_id: Identity used to recognise a redelivery of this event.
        destination: Subscription destination the event arrived on.
    """

    name: str
    url: str
    size: int
    mod_time: str
    event_id: str = ""
    destination: str = ""

    def __str__(self) -> str:
        return f"{self.name} ({self.size} bytes)"


def parse_file_event(
    body: str,
    event_id: str = "",
    destination: str = "",
) -> PelicanEvent:
    """
    Build a `PelicanEvent` from a MESSAGE body.

    Args:
        body: The raw MESSAGE body.
        event_id: Identity to attach, if already computed.
        destination: Destination to attach.

    Returns:
        The parsed event.

    Raises:
        ValueError: If the body is not JSON, or a required field is
            missing or of the wrong type.
    """
    payload = _decode_body(body)

    name = payload.get("name")
    url = payload.get("url")
    size = payload.get("size")
    mod_time = payload.get("mod_time")

    if not isinstance(name, str) or not name:
        raise ValueError("event 'name' must be a non-empty string")
    if not isinstance(url, str) or not url:
        raise ValueError("event 'url' must be a non-empty string")
    # bool is a subclass of int, so it has to be excluded explicitly.
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("event 'size' must be a non-negative integer")
    if not isinstance(mod_time, str) or not mod_time:
        raise ValueError("event 'mod_time' must be a non-empty string")

    return PelicanEvent(
        name=name,
        url=url,
        size=size,
        mod_time=mod_time,
        event_id=event_id,
        destination=destination,
    )


def event_identity(frame: Frame) -> str:
    """
    Work out what makes this event the same event on redelivery.

    The publisher stamps each event with a `uuid`, which survives a
    redelivery. The STOMP `message-id` does not always, so it is only a
    fallback.
    """
    try:
        payload = _decode_body(frame.body)
    except ValueError:
        payload = {}

    identifier = payload.get("uuid")
    if identifier:
        return str(identifier)
    return frame.headers.get("message-id", "unknown-message")


def _decode_body(body: str) -> Dict[str, Any]:
    """Decode a MESSAGE body, unwrapping a JSON-string envelope."""
    try:
        payload: Optional[Any] = json.loads(body)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("event body is not valid JSON") from exc

    # The publisher currently serialises the event as a JSON string
    # inside the STOMP body; accept that as well as a plain object.
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "event body is a JSON string that does not contain JSON"
            ) from exc

    if not isinstance(payload, dict):
        raise ValueError("event body must be a JSON object")
    return payload
