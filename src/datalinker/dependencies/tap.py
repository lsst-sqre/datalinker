"""Dependency that caches information about the TAP schema."""


import yaml

from ..config import config

TAPMetadata = dict[str, dict[str, list[str]]]
"""Type for TAP metadata."""

__all__ = [
    "TAPMetadata",
    "TAPMetadataDependency",
    "tap_metadata_dependency",
]


class TAPMetadataDependency:
    """Maintain a cache of metadata about the TAP schema.

    Some of the datalinker microservices take a parameter specifying what sets
    of columns from a given TAP query to return.  Those column sets are
    defined by metadata present in the Felis schema and generated as part of a
    release of `sdm_schemas <https://github.com/lsst/sdm_schemas>`__.

    This dependency caches that metadata about the tables on first use and
    makes it available to the route handlers.
    """

    def __init__(self) -> None:
        self._columns: TAPMetadata | None = None

    async def __call__(self) -> TAPMetadata:
        """Get column metadata about the TAP schema.

        Returns
        -------
        dict of str to dict of str to list of str
            Mapping from table names (qualified with the schema name) to a
            mapping from column types (``tap:principal`` or ``lsst:minimal``)
            to a list of columns.
        """
        if not self._columns:
            self._columns = self._load_data()
        return self._columns

    def _load_data(self) -> TAPMetadata:
        """Load and cache the schema data."""
        if not config.tap_metadata_dir:
            return {}

        columns: TAPMetadata = {}
        for data_path in config.tap_metadata_dir.iterdir():
            if data_path.suffix != ".yaml":
                continue
            with data_path.open("r") as fh:
                data = yaml.safe_load(fh)

            # Eventually this data will be in a single file, but for now we
            # need to merge the table information for each table from multiple
            # files.
            for table in data["tables"]:
                if table in columns:
                    columns[table].update(data["tables"][table])
                else:
                    columns[table] = data["tables"][table]

        return columns


tap_metadata_dependency = TAPMetadataDependency()
"""The dependency that caches the TAP column metadata."""
