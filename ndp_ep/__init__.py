"""
NDP EP Python Client Library.

A Python client library for interacting with the NDP EP API.
This library provides a simple and intuitive interface for managing
datasets, organizations, resources, and services through the API.
"""

from .api_client import APIClient
from .client_base import APIClientBase
from .dataset_resource_method import APIClientDatasetResource
from .delete_organization_method import APIClientOrganizationDelete
from .delete_resource_method import APIClientResourceDelete
from .get_kafka_details_method import APIClientKafkaDetails
from .get_system_status_method import APIClientSystemStatus
from .get_user_info_method import APIClientUserInfo
from .list_organization_method import APIClientOrganizationList
from .pelican_method import APIClientPelican
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
from .update_service_method import APIClientServiceUpdate
from .update_url_method import APIClientURLUpdate


# Optional dependency: scidx-rexec.
# Expose `ndp_ep.remote_func` lazily so importing ndp_ep works without scidx-rexec.
# (from ndp_ep import remote_func) raises ImportError if scidx-rexec is missing.
from typing import Any

try:
    from rexec.client_api import remote_func as _remote_func
except ImportError:
    _remote_func = None


def __getattr__(name: str) -> Any:
    if name == "remote_func":
        if _remote_func is None:
            raise ImportError(
                "scidx-rexec is required for remote execution. "
                "Install by 'pip install ndp-ep[rexec]'"
            )
        return _remote_func
    raise AttributeError(name)


__version__ = "0.6.0"
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
