# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **The Pelican events tutorial now leads with reading and downloading rather than with plotting.** The notebook opened on a plotting loop and left `pelican_read` and `pelican_fetch` to a closing section about browsing without a subscription, which inverted the story it exists to tell: the library's contribution is that an event hands you a reference you can act on directly, with the Endpoint out of the data path, and drawing a chart is only one thing a reader might then do. The order is now subscribe, inspect an event, read its object into memory, fetch it to disk — each driven by a reference taken from a real event — followed by an explicit divider marking where the library ends and a user's own workflow begins. The plotting example lives after that divider, and the namespace listing has moved below reading, since `pelican_list` is a secondary capability rather than the way into it.

### Fixed
- **The Pelican events tutorial now matches what the event server actually does.** A newly connected subscriber receives nothing for the first few minutes — measured runs waited between two and four — after which the server delivers its queued events in a burst. The notebook assumed events would start arriving immediately, so the cell that reads the raw events bounded its wait at 120 seconds — below that startup delay — and ended having printed nothing, which read as a failure rather than a timeout. Both event loops now wait on a single `EVENT_TIMEOUT` that comfortably exceeds the delay, and the surrounding text describes the burst behaviour. The plotting loop, which previously iterated the subscription with no bound at all and could block indefinitely, is now bounded too.
- **The tutorial no longer presents the end of a `pelican_list` result as the newest data.** The listing is lexicographic, not chronological — `AGMT.CI.LY_.20_c100.csv` sorts before `AGMT.CI.LY_.20_c99.csv` — so `objects[-1]` returned an old object that never changes. The browsing cells now name the object they use explicitly, and the text points to an event's `url` as the way to reach the most recent object.
- Corrected the claim that a new subscriber never receives anything predating its connection: the first burst can include objects written shortly before it subscribed.
- **The events tutorial no longer dies when an event points at an object that has already been deleted.** The demo namespace is a rolling window of 100 objects, roughly the last hour and forty minutes, so a sufficiently stale event names a file the origin will no longer serve — it answers with a `Content-Length` and then zero bytes, which surfaced as an unhandled `ValueError` that stopped the notebook on its first event. The plotting loop now reports and skips such an object instead of failing. The tutorial also stopped shipping `CLIENT_ID = "my-client"`: because the event server keeps one queue per client id, every reader running the notebook unmodified shared a single queue and inherited its accumulated backlog, which is what produced events that stale. The id is now derived from the local username, and the notebook explains the window and the queue.

## [0.8.1] - 2026-08-12

### Fixed
- **Username/password login now reaches the Endpoint.** `get_token()` posted the credentials to `{base_url}/token`, but the Endpoint API exposes login as `POST /user/login` and reads a JSON body, not a form-encoded one. Against a real Endpoint this returned a 404 and no token, so every authenticated call that followed failed. The client now posts a JSON body to `/user/login`; the access token is still read from `access_token`.

## [0.8.0] - 2026-04-11

### Changed
- Version check no longer emits a `UserWarning` when the `/status/` endpoint does not return version information. Instead, an informational message is logged via Python's `logging` module, reducing noise for users whose API server does not yet expose version data.

### Fixed
- Handle `None` response from `set_environment` method

## [0.6.0] - 2026-01-10

### Added
- Remote execution (rexec) support using scidx-rexec
  - `setup_rexec_environment(requirements, token)` - Provision remote execution environments
  - `remote_func` decorator re-exported from scidx-rexec
- Optional dependency `[rexec]` for remote execution features
- PyJWT dependency for token handling

## [0.5.0] - 2025-12-22

### Fixed
- `_check_api_version()` now uses authenticated session for API version check
- Fixes compatibility with API deployments that require authentication for `/status/` endpoint

## [0.4.0] - 2025-12-08

### Added
- Resource operations by ID without requiring dataset_id:
  - `get_resource(resource_id)` - GET /resource/{id}
  - `patch_resource(resource_id, ...)` - PATCH /resource/{id}
  - `delete_resource(resource_id)` - DELETE /resource/{id}
  - `search_resources(q, name, url, format, ...)` - GET /resources/search
- Resource Management tutorial (`docs/source/tutorials/resource_management.ipynb`)

### Features
- Search resources by query, name, url, format, or description
- Pagination support with limit/offset for resource search
- Results include parent dataset context (dataset_id, dataset_name, dataset_title)

## [0.3.0] - 2025-12-01

### Added
- Pelican Federation methods for browsing and downloading from external federations:
  - `list_federations()` - GET /pelican/federations
  - `browse_pelican(path, federation, detail)` - GET /pelican/browse
  - `get_pelican_info(path, federation)` - GET /pelican/info
  - `download_pelican(path, federation, stream)` - GET /pelican/download
  - `import_pelican_metadata(pelican_url, package_id, ...)` - POST /pelican/import-metadata
- Pelican Federation tutorial (`docs/source/tutorials/pelican_federation.ipynb`)

### Fixed
- `create_bucket()` now uses correct API field name (`name` instead of `bucket_name`)

## [0.1.0] - 2025-07-03

### Added
- Initial release of ndp-ep Python client library
- Complete API coverage for all NDP EP endpoints
- Authentication support (token-based and username/password)
- Organization management (create, list, delete)
- Resource registration for multiple types:
  - Kafka topics
  - S3 resources  
  - URL resources
  - Services
  - General datasets
- Resource update functionality (PUT and PATCH operations)
- Resource deletion (by ID and name)
- Search functionality (simple and advanced)
- System information retrieval:
  - System status and health checks
  - System metrics
  - Kafka connection details
  - Jupyter connection details
- Comprehensive error handling with meaningful error messages
- Type hints throughout the codebase
- Extensive test suite with 89% code coverage
- CI/CD pipeline with GitHub Actions
- Automatic PyPI publishing on main branch
- Complete documentation and examples

### Technical Details
- Python 3.8+ support
- Built with requests library for HTTP operations
- Follows PEP 8 coding standards
- Modular architecture with mixin classes
- Comprehensive error handling and validation
- Mock-based testing with requests-mock
- Coverage reporting with pytest-cov
- Code formatting with black
- Linting with flake8
- Type checking with mypy

### API Endpoints Covered
- `/token` - Authentication
- `/organization` - Organization management
- `/kafka` - Kafka topic management
- `/s3` - S3 resource management
- `/url` - URL resource management
- `/services` - Service registration
- `/dataset` - General dataset management
- `/search` - Search functionality
- `/status/*` - System information
- `/resource` - Resource deletion

### Dependencies
- requests >= 2.25.0
- urllib3 >= 1.26.0

### Development Dependencies
- pytest >= 7.0.0
- pytest-cov >= 4.0.0
- pytest-mock >= 3.10.0
- requests-mock >= 1.9.0
- black >= 22.0.0
- flake8 >= 5.0.0
- mypy >= 1.0.0
- twine >= 4.0.0
- build >= 0.10.0
