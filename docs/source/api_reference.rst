API Reference
=============

This section provides detailed documentation for all classes and methods in the ndp-ep library.

.. currentmodule:: ndp_ep

Main Client
-----------

.. autoclass:: APIClient
   :members:
   :inherited-members:
   :show-inheritance:

Base Classes
------------

.. autoclass:: APIClientBase
   :members:
   :show-inheritance:

Organization Management
-----------------------

.. autoclass:: APIClientOrganizationRegister
   :members:
   :show-inheritance:

.. autoclass:: APIClientOrganizationList
   :members:
   :show-inheritance:

.. autoclass:: APIClientOrganizationDelete
   :members:
   :show-inheritance:

Resource Registration
---------------------

.. autoclass:: APIClientKafkaRegister
   :members:
   :show-inheritance:

.. autoclass:: APIClientS3Register
   :members:
   :show-inheritance:

.. autoclass:: APIClientURLRegister
   :members:
   :show-inheritance:

.. autoclass:: APIClientServiceRegister
   :members:
   :show-inheritance:

.. autoclass:: APIClientDatasetRegister
   :members:
   :show-inheritance:

Resource Updates
----------------

.. autoclass:: APIClientKafkaUpdate
   :members:
   :show-inheritance:

.. autoclass:: APIClientS3Update
   :members:
   :show-inheritance:

.. autoclass:: APIClientURLUpdate
   :members:
   :show-inheritance:

.. autoclass:: APIClientDatasetUpdate
   :members:
   :show-inheritance:

Resource Deletion
-----------------

.. autoclass:: APIClientResourceDelete
   :members:
   :show-inheritance:

Search Functionality
--------------------

.. autoclass:: APIClientSearch
   :members:
   :show-inheritance:

System Information
------------------

.. autoclass:: APIClientKafkaDetails
   :members:
   :show-inheritance:

.. autoclass:: APIClientSystemStatus
   :members:
   :show-inheritance:

Constants and Exceptions
------------------------

Version Information
~~~~~~~~~~~~~~~~~~~

.. autodata:: __version__
   :annotation: = "0.1.0"

.. autodata:: __description__
   :annotation: = "Python client library for NDP EP API"

Common Parameters
-----------------

Server Options
~~~~~~~~~~~~~~

Most methods accept a ``server`` parameter with these options:

- ``"local"``: Local CKAN instance
- ``"global"``: Global CKAN instance  
- ``"pre_ckan"``: Pre-production CKAN instance

Authentication
~~~~~~~~~~~~~~

The client supports two authentication methods:

1. **Token-based** (recommended):
   
   .. code-block:: python
   
      client = APIClient(base_url="...", token="your-token")

2. **Username/Password**:
   
   .. code-block:: python
   
      client = APIClient(base_url="...", username="user", password="pass")

Error Handling
--------------

All methods may raise ``ValueError`` with descriptive error messages for:

- Authentication failures
- Network connectivity issues
- API validation errors
- Resource not found errors
- Server configuration errors

Example error handling:

.. code-block:: python

   try:
       result = client.register_organization(org_data)
   except ValueError as e:
       if "already exists" in str(e):
           print("Organization name is taken")
       elif "Authentication failed" in str(e):
           print("Check your credentials")
       else:
           print(f"API error: {e}")

Data Structures
---------------

Organization Data
~~~~~~~~~~~~~~~~~

.. code-block:: python

   org_data = {
       "name": "unique_org_name",        # Required: lowercase, no spaces
       "title": "Organization Title",     # Required: display name
       "description": "Optional description"  # Optional
   }

URL Resource Data
~~~~~~~~~~~~~~~~~

.. code-block:: python

   url_data = {
       "resource_name": "unique_resource_name",  # Required
       "resource_title": "Resource Title",       # Required
       "owner_org": "organization_name",         # Required
       "resource_url": "https://example.com/data.csv",  # Required
       "file_type": "CSV",                       # Optional: CSV, JSON, etc.
       "notes": "Description of the resource",   # Optional
       "extras": {"key": "value"},               # Optional metadata
       "mapping": {"field": "mapping"},          # Optional
       "processing": {"type": "batch"}           # Optional
   }

S3 Resource Data
~~~~~~~~~~~~~~~~

.. code-block:: python

   s3_data = {
       "resource_name": "unique_s3_name",        # Required
       "resource_title": "S3 Resource Title",   # Required  
       "owner_org": "organization_name",         # Required
       "resource_s3": "s3://bucket/path/file",   # Required
       "notes": "Description",                   # Optional
       "extras": {"key": "value"}                # Optional metadata
   }

Kafka Topic Data
~~~~~~~~~~~~~~~~

.. code-block:: python

   kafka_data = {
       "dataset_name": "unique_dataset_name",    # Required
       "dataset_title": "Dataset Title",        # Required
       "owner_org": "organization_name",         # Required
       "kafka_topic": "topic-name",             # Required
       "kafka_host": "kafka.example.com",       # Required
       "kafka_port": "9092",                    # Required
       "dataset_description": "Description",     # Optional
       "extras": {"key": "value"},              # Optional metadata
       "mapping": {"field": "mapping"},         # Optional
       "processing": {"format": "JSON"}         # Optional
   }

Service Data
~~~~~~~~~~~~

.. code-block:: python

   service_data = {
       "service_name": "unique_service_name",    # Required
       "service_title": "Service Title",        # Required
       "owner_org": "services",                 # Required: must be "services"
       "service_url": "https://api.example.com", # Required
       "service_type": "REST API",              # Optional
       "notes": "Service description",          # Optional
       "extras": {"version": "1.0"},           # Optional metadata
       "health_check_url": "https://api.example.com/health",  # Optional
       "documentation_url": "https://docs.example.com"        # Optional
   }

General Dataset Data
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   dataset_data = {
       "name": "unique_dataset_name",           # Required: lowercase, no spaces
       "title": "Dataset Title",               # Required
       "owner_org": "organization_name",        # Required
       "notes": "Dataset description",          # Optional
       "tags": [{"name": "tag1"}, {"name": "tag2"}],  # Optional
       "license_id": "cc-by",                  # Optional
       "version": "1.0",                       # Optional
       "private": False,                       # Optional: default False
       "extras": {"key": "value"},             # Optional metadata
       "resources": [                          # Optional: list of resources
           {
               "name": "resource_name",
               "description": "Resource description", 
               "format": "CSV",
               "url": "https://example.com/data.csv"
           }
       ]
   }

Search Request Data
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Simple search
   terms = ["climate", "temperature"]
   keys = ["title", None]  # Search in title field and globally
   
   # Advanced search
   search_data = {
       "dataset_name": "partial_name",          # Optional
       "resource_url": "partial_url",          # Optional
       "search_term": "term1,term2",           # Optional: comma-separated
       "filter_list": [                        # Optional
           "format:CSV",
           "owner_org:research"
       ],
       "server": "global"                      # Required
   }

Response Formats
----------------

Most registration methods return:

.. code-block:: python

   {
       "id": "generated-resource-id",
       "message": "Success message"
   }

Search methods return a list of dataset objects:

.. code-block:: python

   [
       {
           "id": "dataset-id",
           "name": "dataset-name", 
           "title": "Dataset Title",
           "notes": "Description",
           "organization": {
               "id": "org-id",
               "name": "org-name",
               "title": "Organization Title"
           },
           "resources": [
               {
                   "id": "resource-id",
                   "name": "resource-name",
                   "url": "resource-url",
                   "format": "CSV"
               }
           ],
           "tags": [
               {"name": "tag1"},
               {"name": "tag2"}
           ]
       }
   ]

System status methods return health information:

.. code-block:: python

   {
       "status": "healthy",
       "services": {
           "ckan": "active",
           "keycloak": "active"
       },
       "timestamp": "2024-01-01T12:00:00Z"
   }