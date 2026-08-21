"""Tests for direct Pelican object access."""

from pathlib import Path

import pytest
import requests_mock

from ndp_ep import pelican_data_method
from ndp_ep.pelican_data_method import (
    APIClientPelicanData,
    split_pelican_reference,
)

OSDF = "pelican://osg-htc.org"
PATH_CC = "pelican://path-cc.io"
OBJECT = "/vdc/public/pelican_protocol/AGMT.CI.LY_.20_c36.csv"
PAYLOAD = b"time,east,north,up\n1,0.1,0.2,0.3\n"


class StubPelicanFileSystem:
    """Stand-in for pelicanfs.PelicanFileSystem."""

    contents = {}
    instances = []

    def __init__(self, federation_url):
        self.federation_url = federation_url
        self.cat_calls = []
        self.get_calls = []
        StubPelicanFileSystem.instances.append(self)

    @classmethod
    def reset(cls):
        cls.contents = {}
        cls.instances = []

    def cat_file(self, path):
        self.cat_calls.append(path)
        if path not in self.contents:
            raise FileNotFoundError(path)
        return self.contents[path]

    def get_file(self, rpath, lpath):
        self.get_calls.append((rpath, lpath))
        if rpath not in self.contents:
            raise FileNotFoundError(rpath)
        Path(lpath).write_bytes(self.contents[rpath])


@pytest.fixture
def stub_filesystem(monkeypatch):
    """Replace the optional pelicanfs dependency with a stub."""
    StubPelicanFileSystem.reset()
    monkeypatch.setattr(
        pelican_data_method,
        "_PelicanFileSystem",
        StubPelicanFileSystem,
    )
    return StubPelicanFileSystem


@pytest.fixture
def client():
    """Create a client for the direct Pelican access mixin."""
    with requests_mock.Mocker() as m:
        m.get("http://example.com", status_code=200)
        return APIClientPelicanData(base_url="http://example.com")


class TestSplitPelicanReference:
    """Reference spellings all have to resolve to the same object."""

    @pytest.mark.parametrize(
        "reference",
        [
            "/vdc/public/pelican_protocol/AGMT.CI.LY_.20_c36.csv",
            "vdc/public/pelican_protocol/AGMT.CI.LY_.20_c36.csv",
            "osdf/vdc/public/pelican_protocol/AGMT.CI.LY_.20_c36.csv",
            "osdf://vdc/public/pelican_protocol/AGMT.CI.LY_.20_c36.csv",
            "OSDF://vdc/public/pelican_protocol/AGMT.CI.LY_.20_c36.csv",
            (
                "pelican://osg-htc.org/vdc/public/pelican_protocol/"
                "AGMT.CI.LY_.20_c36.csv"
            ),
            "//vdc//public/pelican_protocol//AGMT.CI.LY_.20_c36.csv",
            "  /vdc/public/pelican_protocol/AGMT.CI.LY_.20_c36.csv  ",
            "/vdc/public/pelican_protocol/AGMT.CI.LY_.20_c36.csv/",
        ],
    )
    def test_equivalent_spellings(self, reference):
        """Every accepted spelling yields the same federation and path."""
        assert split_pelican_reference(reference) == (OSDF, OBJECT)

    def test_pelican_scheme_keeps_its_own_host(self):
        """The host in a pelican:// URL wins over the argument."""
        result = split_pelican_reference(
            "pelican://path-cc.io/foo/bar.csv",
            federation="osdf",
        )
        assert result == (PATH_CC, "/foo/bar.csv")

    def test_alias_segment_selects_federation(self):
        """A leading alias segment selects the federation."""
        result = split_pelican_reference("path-cc/foo/bar.csv")
        assert result == (PATH_CC, "/foo/bar.csv")

    def test_federation_argument_used_when_absent(self):
        """A bare path falls back to the federation argument."""
        result = split_pelican_reference("/foo/bar.csv", federation="path-cc")
        assert result == (PATH_CC, "/foo/bar.csv")

    def test_full_federation_url_argument(self):
        """A full pelican:// URL is accepted as the federation."""
        result = split_pelican_reference(
            "/foo/bar.csv",
            federation="pelican://example.org/",
        )
        assert result == ("pelican://example.org", "/foo/bar.csv")

    @pytest.mark.parametrize("reference", ["", "   ", None, 42])
    def test_empty_reference_rejected(self, reference):
        """An empty or non-string reference is rejected."""
        with pytest.raises(ValueError, match="non-empty string"):
            split_pelican_reference(reference)

    def test_unsupported_scheme_names_the_alternatives(self):
        """An unsupported scheme explains what is accepted instead."""
        with pytest.raises(ValueError, match="Unsupported scheme 's3://'"):
            split_pelican_reference("s3://bucket/key.csv")

    def test_scheme_without_path_rejected(self):
        """A scheme with no object path is rejected."""
        with pytest.raises(ValueError, match="no object path"):
            split_pelican_reference("osdf://")

    def test_pelican_url_without_host_rejected(self):
        """A pelican:// URL missing its host is rejected."""
        with pytest.raises(ValueError, match="missing the federation host"):
            split_pelican_reference("pelican:///vdc/public/a.csv")

    def test_unknown_federation_lists_known_aliases(self):
        """An unknown federation alias lists the known ones."""
        with pytest.raises(ValueError, match="Known aliases: osdf, path-cc"):
            split_pelican_reference("/foo/bar.csv", federation="nope")

    def test_empty_federation_rejected(self):
        """An empty federation argument is rejected."""
        with pytest.raises(ValueError, match="non-empty string"):
            split_pelican_reference("/foo/bar.csv", federation="")


class TestPelicanRead:
    """Reading an object into memory."""

    def test_read_returns_bytes(self, client, stub_filesystem):
        """A successful read returns the object contents."""
        stub_filesystem.contents = {OBJECT: PAYLOAD}

        assert client.pelican_read(f"osdf:/{OBJECT}") == PAYLOAD

    def test_read_normalises_the_path(self, client, stub_filesystem):
        """The filesystem is asked for the normalised path."""
        stub_filesystem.contents = {OBJECT: PAYLOAD}

        client.pelican_read(f"osdf/{OBJECT.lstrip('/')}")

        instance = stub_filesystem.instances[0]
        assert instance.federation_url == OSDF
        assert instance.cat_calls == [OBJECT]

    def test_read_missing_object(self, client, stub_filesystem):
        """A missing object raises a ValueError naming the path."""
        with pytest.raises(ValueError, match="Object not found"):
            client.pelican_read(f"osdf:/{OBJECT}")

    def test_read_wraps_transport_errors(
        self, client, stub_filesystem, monkeypatch
    ):
        """Unexpected filesystem errors surface as ValueError."""

        def explode(self, path):
            raise RuntimeError("director unreachable")

        monkeypatch.setattr(stub_filesystem, "cat_file", explode)

        with pytest.raises(ValueError, match="director unreachable"):
            client.pelican_read(f"osdf:/{OBJECT}")

    def test_filesystem_is_reused(self, client, stub_filesystem):
        """Repeated reads reuse one filesystem per federation."""
        stub_filesystem.contents = {OBJECT: PAYLOAD, "/foo/bar.csv": PAYLOAD}

        client.pelican_read(f"osdf:/{OBJECT}")
        client.pelican_read(f"osdf:/{OBJECT}")
        client.pelican_read("pelican://path-cc.io/foo/bar.csv")

        federations = [i.federation_url for i in stub_filesystem.instances]
        assert federations == [OSDF, PATH_CC]

    def test_read_without_pelicanfs(self, client, monkeypatch):
        """Without the optional dependency the error says how to fix it."""
        monkeypatch.setattr(pelican_data_method, "_PelicanFileSystem", None)

        with pytest.raises(ValueError, match=r"ndp-ep\[pelican\]"):
            client.pelican_read(f"osdf:/{OBJECT}")


class TestPelicanFetch:
    """Downloading an object to disk."""

    def test_fetch_into_directory(self, client, stub_filesystem, tmp_path):
        """A directory destination keeps the object's own name."""
        stub_filesystem.contents = {OBJECT: PAYLOAD}
        destination = tmp_path / "data"

        result = client.pelican_fetch(f"osdf:/{OBJECT}", f"{destination}/")

        assert result == destination / "AGMT.CI.LY_.20_c36.csv"
        assert result.read_bytes() == PAYLOAD

    def test_fetch_creates_missing_parents(
        self, client, stub_filesystem, tmp_path
    ):
        """Missing parent directories are created."""
        stub_filesystem.contents = {OBJECT: PAYLOAD}
        target = tmp_path / "deeply" / "nested" / "out.csv"

        result = client.pelican_fetch(f"osdf:/{OBJECT}", target)

        assert result == target
        assert target.read_bytes() == PAYLOAD

    def test_fetch_to_existing_directory(
        self, client, stub_filesystem, tmp_path
    ):
        """An existing directory is treated as a directory."""
        stub_filesystem.contents = {OBJECT: PAYLOAD}

        result = client.pelican_fetch(f"osdf:/{OBJECT}", tmp_path)

        assert result == tmp_path / "AGMT.CI.LY_.20_c36.csv"

    def test_fetch_refuses_to_overwrite(
        self, client, stub_filesystem, tmp_path
    ):
        """An existing target is an error rather than a silent overwrite."""
        stub_filesystem.contents = {OBJECT: PAYLOAD}
        target = tmp_path / "out.csv"
        target.write_bytes(b"keep me")

        with pytest.raises(ValueError, match="already exists"):
            client.pelican_fetch(f"osdf:/{OBJECT}", target)

        assert target.read_bytes() == b"keep me"

    def test_fetch_overwrites_when_asked(
        self, client, stub_filesystem, tmp_path
    ):
        """overwrite=True replaces the existing target."""
        stub_filesystem.contents = {OBJECT: PAYLOAD}
        target = tmp_path / "out.csv"
        target.write_bytes(b"replace me")

        client.pelican_fetch(f"osdf:/{OBJECT}", target, overwrite=True)

        assert target.read_bytes() == PAYLOAD

    def test_fetch_missing_object(self, client, stub_filesystem, tmp_path):
        """A missing object raises a ValueError naming the path."""
        with pytest.raises(ValueError, match="Object not found"):
            client.pelican_fetch(f"osdf:/{OBJECT}", tmp_path / "out.csv")

    def test_fetch_wraps_transport_errors(
        self, client, stub_filesystem, tmp_path, monkeypatch
    ):
        """Unexpected filesystem errors surface as ValueError."""

        def explode(self, rpath, lpath):
            raise RuntimeError("transfer aborted")

        monkeypatch.setattr(stub_filesystem, "get_file", explode)

        with pytest.raises(ValueError, match="transfer aborted"):
            client.pelican_fetch(f"osdf:/{OBJECT}", tmp_path / "out.csv")

    def test_scheme_without_path_rejected_early(
        self, client, stub_filesystem, tmp_path
    ):
        """A scheme with no object path fails before touching the disk."""
        with pytest.raises(ValueError, match="no object path"):
            client.pelican_fetch("osdf://", tmp_path)

    def test_root_reference_into_directory(
        self, client, stub_filesystem, tmp_path
    ):
        """A bare federation alias has no object name either."""
        with pytest.raises(ValueError, match="Cannot derive a file name"):
            client.pelican_fetch("osdf", tmp_path)
