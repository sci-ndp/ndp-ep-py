"""Tests for the Pelican event wire format."""

import json

import pytest

from ndp_ep._pelican_protocol import (
    Frame,
    escape_header,
    event_identity,
    is_heartbeat,
    parse_file_event,
    parse_frame,
    unescape_header,
    websocket_url,
)


def event_body(**overrides):
    """Build a well-formed event body, with fields overridden."""
    payload = {
        "name": "AGMT.CI.LY_.20_c36.csv",
        "url": "osdf://vdc/public/pelican_protocol/AGMT.CI.LY_.20_c36.csv",
        "size": 3724,
        "mod_time": "2026-08-21T09:00:00Z",
        "uuid": "e4d1-uuid",
    }
    payload.update(overrides)
    return json.dumps(payload)


class TestHeaderEscaping:
    """STOMP 1.2 header escaping."""

    @pytest.mark.parametrize(
        "value",
        [
            "plain",
            "with:colon",
            "with\nnewline",
            "with\rcarriage",
            "with\\backslash",
            "all\\of:them\nat\ronce",
            "",
        ],
    )
    def test_round_trip(self, value):
        """Escaping and unescaping returns the original value."""
        assert unescape_header(escape_header(value)) == value

    def test_escaped_backslash_is_not_read_twice(self):
        """A literal backslash followed by 'n' is not a newline."""
        assert unescape_header(escape_header("\\n")) == "\\n"

    def test_unknown_escape_keeps_the_character(self):
        """An unrecognised escape yields the escaped character itself."""
        assert unescape_header("\\q") == "q"

    def test_trailing_backslash_is_literal(self):
        """A trailing backslash has nothing to escape."""
        assert unescape_header("abc\\") == "abc\\"


class TestFrames:
    """Frame encoding and parsing."""

    def test_encode_with_headers(self):
        """Headers are emitted one per line before a blank line."""
        frame = Frame("SEND", {"destination": "/queue/a"}, "hello")

        assert frame.encode() == b"SEND\ndestination:/queue/a\n\nhello\x00"

    def test_encode_without_headers(self):
        """A frame with no headers has exactly one blank line."""
        assert Frame("DISCONNECT").encode() == b"DISCONNECT\n\n\x00"

    def test_round_trip(self):
        """Parsing an encoded frame returns the original."""
        original = Frame(
            "MESSAGE",
            {"destination": "sub/osdf/a", "message-id": "42"},
            '{"a": 1}',
        )

        parsed = parse_frame(original.encode())

        assert parsed.command == "MESSAGE"
        assert parsed.headers == original.headers
        assert parsed.body == original.body

    def test_round_trip_with_escaped_values(self):
        """Values needing escapes survive the round trip."""
        original = Frame("MESSAGE", {"note": "a:b\nc"}, "")

        assert parse_frame(original.encode()).headers["note"] == "a:b\nc"

    def test_repeated_header_keeps_the_first(self):
        """STOMP 1.2 requires the first value of a repeated header."""
        raw = b"MESSAGE\nid:first\nid:second\n\nbody\x00"

        assert parse_frame(raw).headers["id"] == "first"

    def test_body_may_contain_blank_lines(self):
        """Only the first blank line separates headers from body."""
        raw = b"MESSAGE\nid:1\n\nline\n\nline\x00"

        assert parse_frame(raw).body == "line\n\nline"

    def test_parse_without_trailing_nul(self):
        """A frame is still parsed if the NUL is absent."""
        assert parse_frame(b"CONNECTED\nversion:1.2\n\n").command == (
            "CONNECTED"
        )

    @pytest.mark.parametrize("raw", [b"\n", b"\r\n"])
    def test_heartbeat_recognised(self, raw):
        """Bare line endings are heartbeats, not frames."""
        assert is_heartbeat(raw) is True

    def test_frame_is_not_a_heartbeat(self):
        """A real frame is not mistaken for a heartbeat."""
        assert is_heartbeat(b"MESSAGE\n\n\x00") is False


class TestWebsocketUrl:
    """URL conversion."""

    @pytest.mark.parametrize(
        "given,expected",
        [
            ("https://server.org/ws", "wss://server.org/ws"),
            ("http://server.org/ws", "ws://server.org/ws"),
            ("wss://server.org/ws", "wss://server.org/ws"),
            ("ws://localhost:8080", "ws://localhost:8080"),
        ],
    )
    def test_conversion(self, given, expected):
        """http(s) becomes ws(s) and ws(s) is left alone."""
        assert websocket_url(given) == expected

    @pytest.mark.parametrize(
        "given", ["ftp://server.org", "server.org/ws", "", "https://"]
    )
    def test_rejects_unusable_urls(self, given):
        """A URL without a host or a usable scheme is rejected."""
        with pytest.raises(ValueError, match="http\\(s\\) or ws\\(s\\)"):
            websocket_url(given)


class TestParseFileEvent:
    """The application payload carried in a MESSAGE body."""

    def test_valid_event(self):
        """A well-formed body produces a populated event."""
        event = parse_file_event(event_body(), "id-1", "sub/osdf/a")

        assert event.name == "AGMT.CI.LY_.20_c36.csv"
        assert event.size == 3724
        assert event.mod_time == "2026-08-21T09:00:00Z"
        assert event.event_id == "id-1"
        assert event.destination == "sub/osdf/a"

    def test_json_string_envelope(self):
        """A body that is a JSON string containing JSON is unwrapped."""
        wrapped = json.dumps(event_body())

        assert parse_file_event(wrapped).name == "AGMT.CI.LY_.20_c36.csv"

    def test_str_is_readable(self):
        """The event prints as something a human can read."""
        assert "3724 bytes" in str(parse_file_event(event_body()))

    def test_event_is_hashable(self):
        """Events can go in a set, being frozen."""
        assert len({parse_file_event(event_body())}) == 1

    @pytest.mark.parametrize(
        "body,message",
        [
            ("not json", "not valid JSON"),
            ('"still not json"', "does not contain JSON"),
            ("[1, 2]", "must be a JSON object"),
        ],
    )
    def test_undecodable_bodies(self, body, message):
        """A body that is not a JSON object is rejected."""
        with pytest.raises(ValueError, match=message):
            parse_file_event(body)

    @pytest.mark.parametrize(
        "overrides,message",
        [
            ({"name": ""}, "'name'"),
            ({"name": 5}, "'name'"),
            ({"url": ""}, "'url'"),
            ({"size": -1}, "'size'"),
            ({"size": "3724"}, "'size'"),
            ({"size": True}, "'size'"),
            ({"mod_time": ""}, "'mod_time'"),
        ],
    )
    def test_invalid_fields(self, overrides, message):
        """Each required field is checked for type and value."""
        with pytest.raises(ValueError, match=message):
            parse_file_event(event_body(**overrides))

    def test_missing_field(self):
        """An absent field is reported like an invalid one."""
        payload = json.loads(event_body())
        del payload["url"]

        with pytest.raises(ValueError, match="'url'"):
            parse_file_event(json.dumps(payload))


class TestEventIdentity:
    """What makes a redelivered event the same event."""

    def test_uuid_wins(self):
        """The publisher's uuid identifies the event."""
        frame = Frame("MESSAGE", {"message-id": "server-1"}, event_body())

        assert event_identity(frame) == "e4d1-uuid"

    def test_falls_back_to_message_id(self):
        """Without a uuid, the STOMP message id is used."""
        payload = json.loads(event_body())
        del payload["uuid"]
        frame = Frame(
            "MESSAGE", {"message-id": "server-1"}, json.dumps(payload)
        )

        assert event_identity(frame) == "server-1"

    def test_unreadable_body_falls_back(self):
        """A body that is not JSON still yields an identity."""
        frame = Frame("MESSAGE", {"message-id": "server-1"}, "garbage")

        assert event_identity(frame) == "server-1"

    def test_last_resort(self):
        """With neither uuid nor message id, identity is a constant."""
        assert event_identity(Frame("MESSAGE", {}, "garbage")) == (
            "unknown-message"
        )
