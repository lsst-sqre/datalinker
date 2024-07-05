# Change log

datalinker is versioned with [semver](https://semver.org/). Dependencies are updated to the latest available version during each release. Those changes are not noted here explicitly.

Find changes for the upcoming release in the project's [changelog.d directory](https://github.com/lsst-sqre/datalinker/tree/main/changelog.d/).

<!-- scriv-insert-here -->

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
