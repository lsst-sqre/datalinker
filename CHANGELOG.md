# Change log

datalinker is versioned with [semver](https://semver.org/). Dependencies are updated to the latest available version during each release. Those changes are not noted here explicitly.

Find changes for the upcoming release in the project's [changelog.d directory](https://github.com/lsst-sqre/datalinker/tree/main/changelog.d/).

<!-- scriv-insert-here -->

<a id='changelog-3.3.0'></a>
## 3.3.0 (2025-06-18)

### New features

- Change Config to load configuration from local file, to support more complex structures for the hips release data
- Introduce v2 hips router. Add an additional hips dependency that builds a hips list per data release, given the data release lists and their paths via configuration
- Add new tests for v2 and legacy hips list endpoint

### Other changes

- Drop `Expires` from the reply headers of the `{links}` endpoint, since that header is effectively obsolete since HTTP/1.1 given the presence of `Cache-Control` with a `max-age` parameter.

- Upgraded dependencies and python version

<a id='changelog-3.2.0'></a>
## 3.2.0 (2025-04-11)

### New features

- Set `Expires` and `Cache-Control` headers on the links reply reflecting the expiration time of signed image URLs, informing clients that the response should not be cached beyond the expiration of those URLs. The lifetime of the links is specified as a new configuration option for now. That option will be removed once that lifetime is available from Butler.

### Other changes

- datalinker now requires [uv](https://docs.astral.sh/uv/) for development and frozen dependencies.

<a id='changelog-3.1.0'></a>
## 3.1.0 (2025-02-20)

### New features

- Use `lsst.daf.butler` to parse Butler URIs rather than doing the parsing internally. This adds support for the new Butler URI format that will be used for future data releases.

<a id='changelog-3.0.0'></a>
## 3.0.0 (2024-08-02)

### Backwards-incompatible changes

- Drop support for direct Butler and require client/server Butler.

<a id='changelog-2.0.0'></a>
## 2.0.0 (2024-06-28)

### Backwards-incompatible changes

- Update to a new version of `lsst.daf.butler`, which changes the REST API implementation in a backward-incompatible way to match the new release of the Butler server.

<a id='changelog-1.7.1'></a>
## 1.7.1 (2024-04-11)

### Bug fixes

- Update lsst-resources, fixing a memory leak.

### Other changes

- Update to the latest Butler client, which may require running an equally new version of the Butler server.

<a id='changelog-1.7.0'></a>
## 1.7.0 (2024-01-26)

### New features

- Add support for querying the Butler server for images rather than instantiating local Butler instances. To support this, datalinker now requests delegated tokens from Gafaelfawr so that it can make API calls on behalf of the user.
- Standardize using a `DATALINKER_` prefix for all environment variables used to configure datalinker.
- Diagnose more errors in environment variable settings and fail on startup if the configuration is not valid.
- Add support for reporting uncaught exceptions to a Slack incoming webhook.
- Support configuration of the DataLink and HiPS URL prefixes on which datalinker should listen.
- Configure Uvicorn to log accesses in a JSON format if datalinker is configured to use the production logging profile.

### Bug fixes

- Validate the configuration parameters passed via environment variables and error out early if they are set to invalid values.

### Other changes

- Add a change log maintained using [scriv](https://scriv.readthedocs.io/en/latest/).
- Use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting instead of Black, flake8, and isort.
