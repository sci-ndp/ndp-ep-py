"""Direct access to Pelican federation objects.

The methods in this module read and download objects straight from a
Pelican federation, inside the caller's own process. Nothing goes through
the NDP Endpoint. This is the counterpart of ``pelican_method``, whose
``browse_pelican``/``download_pelican`` proxy the same federations through
the Endpoint API.

Requires the optional ``pelicanfs`` dependency::

    pip install ndp-ep[pelican]
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Tuple, Union

from .client_base import APIClientBase

try:
    from pelicanfs import PelicanFileSystem as _PelicanFileSystem
except ImportError:  # pragma: no cover - optional dependency at runtime
    _PelicanFileSystem = None


# Federation aliases accepted in object references and in the `federation`
# argument, mapped to the discovery URL of that federation.
FEDERATION_URLS: Dict[str, str] = {
    "osdf": "pelican://osg-htc.org",
    "path-cc": "pelican://path-cc.io",
}

DEFAULT_FEDERATION = "osdf"


def _clean_path(path: str) -> str:
    """
    Normalise a namespace path to a single leading slash.

    Collapses repeated separators and drops any trailing separator, so
    that equivalent spellings of the same object produce the same string.
    """
    segments = [segment for segment in path.split("/") if segment]
    return "/" + "/".join(segments)


def _federation_url(federation: str) -> str:
    """
    Resolve a federation alias, or a full URL, to a discovery URL.

    Args:
        federation: Alias such as "osdf", or a full "pelican://host" URL.

    Returns:
        The federation discovery URL.

    Raises:
        ValueError: If the alias is unknown.
    """
    fed = (federation or "").strip()
    if not fed:
        raise ValueError("Federation must be a non-empty string.")
    if fed in FEDERATION_URLS:
        return FEDERATION_URLS[fed]
    if fed.startswith("pelican://"):
        return fed.rstrip("/")
    known = ", ".join(sorted(FEDERATION_URLS))
    raise ValueError(
        f"Unknown federation '{federation}'. Known aliases: {known}. "
        "Alternatively pass a full 'pelican://<host>' URL."
    )


def split_pelican_reference(
    reference: str,
    federation: str = DEFAULT_FEDERATION,
) -> Tuple[str, str]:
    """
    Split an object reference into a federation URL and namespace path.

    References to the same object legitimately reach users in several
    spellings, depending on whether they came from an event payload, a
    federation listing or a human. All of the following denote the same
    object and are accepted:

    - ``/vdc/public/data/file.csv`` (bare namespace path)
    - ``vdc/public/data/file.csv`` (no leading slash)
    - ``osdf/vdc/public/data/file.csv`` (federation alias as first segment)
    - ``osdf://vdc/public/data/file.csv``
    - ``pelican://osg-htc.org/vdc/public/data/file.csv``

    Note that in the ``osdf://`` form the component after the scheme is
    *not* a host: the whole remainder is the namespace path. In the
    ``pelican://`` form the first component *is* the federation host.

    Args:
        reference: The object reference, in any of the forms above.
        federation: Federation to assume when the reference does not name
            one. Alias or full "pelican://host" URL.

    Returns:
        Tuple of (federation discovery URL, normalised namespace path).

    Raises:
        ValueError: If the reference is empty, uses an unsupported scheme,
            or names an unknown federation.

    Example:
        >>> split_pelican_reference("osdf://vdc/public/a.csv")
        ('pelican://osg-htc.org', '/vdc/public/a.csv')
    """
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("Pelican reference must be a non-empty string.")

    ref = reference.strip()

    if "://" in ref:
        scheme, _, remainder = ref.partition("://")
        scheme = scheme.lower()
        if not remainder.strip("/"):
            raise ValueError(
                f"Pelican reference '{reference}' has no object path."
            )
        if scheme == "pelican":
            host, _, path = remainder.partition("/")
            if not host:
                raise ValueError(
                    f"Pelican reference '{reference}' is missing the "
                    "federation host."
                )
            return f"pelican://{host}", _clean_path(path)
        if scheme in FEDERATION_URLS:
            return FEDERATION_URLS[scheme], _clean_path(remainder)
        raise ValueError(
            f"Unsupported scheme '{scheme}://' in Pelican reference "
            f"'{reference}'. Use 'pelican://<host>/<path>', "
            "'osdf://<path>', or a bare namespace path."
        )

    segments = [segment for segment in ref.split("/") if segment]
    if segments and segments[0].lower() in FEDERATION_URLS:
        alias = segments[0].lower()
        return FEDERATION_URLS[alias], _clean_path("/".join(segments[1:]))

    return _federation_url(federation), _clean_path(ref)


class APIClientPelicanData(APIClientBase):
    """Extension of APIClientBase with direct Pelican object access."""

    # Populated lazily by _pelican_filesystem; one filesystem per
    # federation, so repeated reads reuse the same director discovery.
    _pelican_fs_cache: Dict[str, Any]

    def pelican_read(
        self,
        reference: str,
        federation: str = DEFAULT_FEDERATION,
    ) -> bytes:
        """
        Read a Pelican object into memory, without writing to disk.

        The transfer happens between the caller's process and the
        federation; the NDP Endpoint is not involved.

        Args:
            reference: Object reference. See `split_pelican_reference`
                for the accepted forms.
            federation: Federation to assume when the reference does not
                name one (default "osdf").

        Returns:
            The object contents as bytes.

        Raises:
            ValueError: If pelicanfs is not installed, the reference is
                invalid, or the object cannot be read.

        Example:
            >>> raw = client.pelican_read("osdf://vdc/public/a.csv")
            >>> df = pd.read_csv(io.BytesIO(raw))
        """
        federation_url, path = split_pelican_reference(reference, federation)
        filesystem = self._pelican_filesystem(federation_url)

        try:
            content = filesystem.cat_file(path)
        except FileNotFoundError as exc:
            raise ValueError(
                f"Object not found in {federation_url}: {path}"
            ) from exc
        except Exception as exc:
            raise ValueError(
                f"Error reading {path} from {federation_url}: {exc}"
            ) from exc

        return bytes(content)

    def pelican_fetch(
        self,
        reference: str,
        destination: Union[str, Path],
        federation: str = DEFAULT_FEDERATION,
        overwrite: bool = False,
    ) -> Path:
        """
        Download a Pelican object to a local path.

        Args:
            reference: Object reference. See `split_pelican_reference`
                for the accepted forms.
            destination: Target file, or a directory in which to place the
                object under its own name. A value that already exists as
                a directory, or that ends in a separator, is treated as a
                directory. Missing parent directories are created.
            federation: Federation to assume when the reference does not
                name one (default "osdf").
            overwrite: Replace the target if it already exists. When
                False (the default) an existing target is an error rather
                than a silent overwrite.

        Returns:
            Path of the written file.

        Raises:
            ValueError: If pelicanfs is not installed, the reference is
                invalid, the target exists and overwrite is False, or the
                download fails.

        Example:
            >>> client.pelican_fetch("osdf://vdc/public/a.csv", "./data/")
            PosixPath('data/a.csv')
        """
        federation_url, path = split_pelican_reference(reference, federation)
        target = self._resolve_destination(destination, path)

        if target.exists() and not overwrite:
            raise ValueError(
                f"Destination already exists: {target}. "
                "Pass overwrite=True to replace it."
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        filesystem = self._pelican_filesystem(federation_url)

        try:
            filesystem.get_file(path, str(target))
        except FileNotFoundError as exc:
            raise ValueError(
                f"Object not found in {federation_url}: {path}"
            ) from exc
        except Exception as exc:
            raise ValueError(
                f"Error downloading {path} from {federation_url}: {exc}"
            ) from exc

        return target

    @staticmethod
    def _resolve_destination(
        destination: Union[str, Path],
        path: str,
    ) -> Path:
        """
        Work out the file to write for a destination and a namespace path.
        """
        target = Path(destination)
        raw = str(destination)
        is_directory = target.is_dir() or raw.endswith(("/", os.sep))

        if not is_directory:
            return target

        name = path.rsplit("/", 1)[-1]
        if not name:
            raise ValueError(
                f"Cannot derive a file name from reference path '{path}'. "
                "Give an explicit destination file."
            )
        return target / name

    def _pelican_filesystem(self, federation_url: str) -> Any:
        """
        Return a cached PelicanFileSystem for a federation.
        """
        filesystem_class = self._require_pelicanfs()

        cache = getattr(self, "_pelican_fs_cache", None)
        if cache is None:
            cache = {}
            self._pelican_fs_cache = cache

        if federation_url not in cache:
            cache[federation_url] = filesystem_class(federation_url)
        return cache[federation_url]

    @staticmethod
    def _require_pelicanfs() -> Any:
        if (
            _PelicanFileSystem is None
        ):  # pragma: no cover - depends on optional install
            raise ValueError(
                "pelicanfs is not installed. Install it with "
                "'pip install ndp-ep[pelican]' to read Pelican objects "
                "directly."
            )
        return _PelicanFileSystem
