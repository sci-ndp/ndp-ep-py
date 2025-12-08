"""
NDP EP Python Client Library.

A Python client library for interacting with the NDP EP API.
This library provides a simple and intuitive interface for managing
datasets, organizations, resources, and services through the API.
"""

from .api_client import APIClient
from .client_base import APIClientBase
from .delete_organization_method import APIClientOrganizationDelete
from .delete_resource_method import APIClientResourceDelete
from .get_kafka_details_method import APIClientKafkaDetails
from .get_system_status_method import APIClientSystemStatus
from .list_organization_method import APIClientOrganizationList
from .register_dataset_method import APIClientDatasetRegister
from .register_kafka_method import APIClientKafkaRegister
from .register_organization_method import APIClientOrganizationRegister
from .register_s3_method import APIClientS3Register
from .register_service_method import APIClientServiceRegister
from .register_url_method import APIClientURLRegister
from .search_method import APIClientSearch
from .update_dataset_method import APIClientDatasetUpdate
from .update_kafka_method import APIClientKafkaUpdate
from .update_s3_method import APIClientS3Update
from .update_url_method import APIClientURLUpdate

# Optional convenience export for the remote execution decorator.
try:  # pragma: no cover - depends on optional SciDx-rexec install
    from rexec.client_api import remote_func as remote_func  # type: ignore
except ImportError as exc:  # pragma: no cover
    class _RemoteFuncProxy:
        """
        Lazy proxy that raises a helpful error if SciDx-rexec is missing.
        """

        def __init__(self, error: ImportError):
            self._error = error
            self._target = None

        def _load(self):
            if self._target is None:
                try:
                    from rexec.client_api import remote_func as _rf  # type: ignore
                except ImportError as err:
                    raise ImportError(
                        "SciDx-rexec is required for remote execution. "
                        "Install 'ndp-ep[rexec]' to use ndp_ep.remote_func."
                    ) from err
                self._target = _rf
            return self._target

        def __call__(self, *args, **kwargs):
            return self._load()(*args, **kwargs)

        def __getattr__(self, item):
            return getattr(self._load(), item)

        def __setattr__(self, name, value):
            if name in {"_error", "_target"}:
                object.__setattr__(self, name, value)
            else:
                setattr(self._load(), name, value)

    remote_func = _RemoteFuncProxy(exc)

__version__ = "0.1.1"
__description__ = "Python client library for NDP EP API"

# Main exports
__all__ = [
    "APIClient",
    "APIClientBase",
    "remote_func",
    "__version__",
    "__description__",
]

# Default client for backward compatibility
Client = APIClient
