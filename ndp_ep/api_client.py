"""Unified API Client combining all functionality."""

from .dataset_resource_method import APIClientDatasetResource
from .delete_organization_method import APIClientOrganizationDelete
from .delete_resource_method import APIClientResourceDelete
from .get_kafka_details_method import APIClientKafkaDetails
from .pelican_method import APIClientPelican
from .get_system_status_method import APIClientSystemStatus
from .get_user_info_method import APIClientUserInfo
from .list_organization_method import APIClientOrganizationList
from .register_dataset_method import APIClientDatasetRegister
from .register_kafka_method import APIClientKafkaRegister
from .register_organization_method import APIClientOrganizationRegister
from .register_s3_method import APIClientS3Register
from .register_service_method import APIClientServiceRegister
from .register_url_method import APIClientURLRegister
from .s3_buckets_method import APIClientS3Buckets
from .s3_objects_method import APIClientS3Objects
from .search_method import APIClientSearch
from .update_dataset_method import APIClientDatasetUpdate
from .update_kafka_method import APIClientKafkaUpdate
from .update_s3_method import APIClientS3Update
from .update_service_method import APIClientServiceUpdate
from .update_url_method import APIClientURLUpdate


class APIClient(
    APIClientKafkaRegister,
    APIClientOrganizationRegister,
    APIClientS3Register,
    APIClientURLRegister,
    APIClientServiceRegister,
    APIClientDatasetRegister,
    APIClientOrganizationList,
    APIClientSearch,
    APIClientKafkaUpdate,
    APIClientS3Update,
    APIClientServiceUpdate,
    APIClientURLUpdate,
    APIClientDatasetUpdate,
    APIClientDatasetResource,
    APIClientOrganizationDelete,
    APIClientResourceDelete,
    APIClientKafkaDetails,
    APIClientSystemStatus,
    APIClientUserInfo,
    APIClientS3Buckets,
    APIClientS3Objects,
    APIClientPelican,
):
    """
    Unified API Client with comprehensive functionality.

    This class combines all the individual API client mixins to provide
    a complete interface for interacting with the NDP EP API.

    Features:
    - Organization management (create, list, delete)
    - Resource registration (Kafka, S3, URL, Services, General datasets)
    - Resource updates (Kafka, S3, URL, Services, General datasets)
    - Resource deletion (by ID, name, or from dataset)
    - Search functionality (simple and advanced)
    - System information (status, metrics, Kafka details, Jupyter details)
    - User information (get current authenticated user details)
    - S3 buckets management (create, list, delete, get info)
    - S3 objects management (upload, download, delete, list, metadata)
    - Pelican federation (browse, download, import metadata)
    - Authentication (token-based and username/password)

    Example:
        >>> client = APIClient(
        ...     base_url="https://api.example.com",
        ...     token="your-token"
        ... )
        >>> organizations = client.list_organizations()
        >>> results = client.search_datasets(["climate"], server="global")
    """

    pass
