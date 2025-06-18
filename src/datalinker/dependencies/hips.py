"""HiPS list cache."""

import re
from abc import ABC, abstractmethod
from typing import Annotated

from fastapi import Depends, HTTPException
from httpx import AsyncClient
from pydantic import HttpUrl
from safir.dependencies.http_client import http_client_dependency
from safir.dependencies.logger import logger_dependency
from structlog.stdlib import BoundLogger

from ..config import Config
from .config import config_dependency

__all__ = [
    "DatasetHiPSListDependency",
    "HiPSListDependency",
    "dataset_hips_list_dependency",
    "hips_list_dependency",
]


class BaseHiPSListDependency(ABC):
    """Base class with common HiPS list functionality."""

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear the cached HiPS data."""

    async def _fetch_and_process_properties(
        self,
        *,
        base_url: HttpUrl,
        hips_path: str,
        client: AsyncClient,
        logger: BoundLogger,
        config: Config,
        dataset: str | None = None,
    ) -> str | None:
        """Fetch and process a single HiPS properties file.

        Parameters
        ----------
        base_url
            Base URL for the HiPS service.
        hips_path
            Path to the specific HiPS dataset.
        client
            HTTP client for making requests.
        logger
            Logger for error messages.
        config
            Configuration object containing auth token.
        dataset
            Optional dataset name for logging context.

        Returns
        -------
        str | None
            Processed properties data, or None if fetch failed.
        """
        url = str(base_url).rstrip("/") + f"/{hips_path}"
        r = await client.get(
            url + "/properties",
            headers={"Authorization": f"bearer {config.token}"},
        )
        if r.status_code != 200:
            log_msg = "Unable to get HiPS properties"
            log_context = {
                "url": url,
                "status": r.status_code,
                "error": r.reason_phrase,
            }
            if dataset:
                log_msg += " for dataset"
                log_context["dataset"] = dataset

            logger.warning(log_msg, **log_context)
            return None

        # Our HiPS properties files don't contain the URL
        # (hips_service_url), but this is mandatory in the entries in the
        # HiPS list.  Add it before hips_status.
        service_url = "{:25}= {}".format("hips_service_url", url)
        return re.sub(
            "^hips_status",
            f"{service_url}\nhips_status",
            r.text,
            flags=re.MULTILINE,
        )

    async def build_hips_list_from_paths(
        self,
        *,
        base_url: HttpUrl,
        hips_paths: list[str],
        client: AsyncClient,
        logger: BoundLogger,
        config: Config,
        dataset: str | None = None,
    ) -> str:
        """Build HiPS list from a collection of paths.

        Parameters
        ----------
        base_url
            Base URL for the HiPS service.
        hips_paths
            List of HiPS dataset paths.
        client
            HTTP client for making requests.
        logger
            Logger for error messages.
        config
            Configuration object.
        dataset
            Optional dataset name for logging context.

        Returns
        -------
        str
            Concatenated HiPS list from all successful fetches.
        """
        lists = []
        for hips_path in hips_paths:
            data = await self._fetch_and_process_properties(
                base_url=base_url,
                hips_path=hips_path,
                client=client,
                logger=logger,
                config=config,
                dataset=dataset,
            )
            if data:
                lists.append(data)

        # The HiPS list is the concatenation of all the properties files
        # separated by blank lines.
        return "\n".join(lists)


class HiPSListDependency(BaseHiPSListDependency):
    """Maintain a cache of HiPS properties files for this deployment.

    A deployment of the Science Platform may have several trees of HiPS data
    served out of GCS.  Those need to be gathered together and served as a
    unified HiPS list of all available trees.  Rather than making multiple API
    calls to GCS each time this list is requested, cache the HiPS list
    constructed from the ``properties`` files and prefer to serve them from
    the cache.

    Provides backward compatibility for the legacy /api/hips/list endpoint.
    Uses either the legacy hips_base_url (for full backward compatibility)
    or the configured default dataset from hips_datasets if specified.
    """

    def __init__(self) -> None:
        self._hips_list: str | None = None

    def clear_cache(self) -> None:
        """Clear the cached HiPS list."""
        self._hips_list = None

    async def __call__(
        self,
        client: Annotated[AsyncClient, Depends(http_client_dependency)],
        logger: Annotated[BoundLogger, Depends(logger_dependency)],
    ) -> str:
        if not self._hips_list:
            self._hips_list = await self._build_hips_list(client, logger)
        return self._hips_list

    async def _build_hips_list(
        self, client: AsyncClient, logger: BoundLogger
    ) -> str:
        """Retrieve and cache properties files for all HiPS data sets.

        If no HiPS datasets are configured, returns an empty HiPS list.

        Parameters
        ----------
        client
            Client to use to retrieve the HiPS lists.
        logger
            Logger for any error messages.

        Returns
        -------
        str
            The HiPS list content, or empty string if no datasets configured.
        """
        config = config_dependency.config()

        if (
            not config.hips_datasets
            or not config.hips_default_dataset
            or config.hips_default_dataset not in config.hips_datasets
        ):
            return ""

        dataset_config = config.hips_datasets[config.hips_default_dataset]
        base_url = dataset_config.url
        hips_paths = dataset_config.paths

        return await self.build_hips_list_from_paths(
            base_url=base_url,
            hips_paths=hips_paths,
            client=client,
            logger=logger,
            config=config,
            dataset=config.hips_default_dataset,
        )


class DatasetHiPSListDependency(BaseHiPSListDependency):
    """Maintain a cache of HiPS properties files for individual datasets.

    This handles the new v2 API where each dataset (e.g., 'dp02', 'dp1')
    has its own base URL and serves from different GCS buckets via
    /api/hips/v2/{dataset}/ endpoints.
    """

    def __init__(self) -> None:
        self._hips_lists: dict[str, str] = {}

    def clear_cache(self) -> None:
        """Clear all cached HiPS lists for all datasets."""
        self._hips_lists.clear()

    def clear_dataset_cache(self, dataset: str) -> None:
        """Clear the cached HiPS list for a specific dataset.

        Parameters
        ----------
        dataset
            The dataset name to clear from cache.
        """
        self._hips_lists.pop(dataset, None)

    async def __call__(
        self,
        dataset: str,
        client: Annotated[AsyncClient, Depends(http_client_dependency)],
        logger: Annotated[BoundLogger, Depends(logger_dependency)],
    ) -> str:
        config = config_dependency.config()

        if not config.has_hips_datasets():
            raise HTTPException(
                status_code=404, detail="No HiPS datasets are configured"
            )

        # Check if the specific dataset exists
        if dataset not in config.hips_datasets:
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{dataset}' not configured. "
                f"Available datasets: "
                f"{list(config.hips_datasets.keys())}",
            )

        if dataset not in self._hips_lists:
            self._hips_lists[dataset] = await self._build_dataset_hips_list(
                dataset, client, logger
            )
        return self._hips_lists[dataset]

    async def _build_dataset_hips_list(
        self, dataset: str, client: AsyncClient, logger: BoundLogger
    ) -> str:
        """Retrieve and cache properties files for a specific dataset.

        Parameters
        ----------
        dataset
            The dataset name (key in hips_datasets config).
        client
            Client to use to retrieve the HiPS lists.
        logger
            Logger for any error messages.
        """
        config = config_dependency.config()
        dataset_config = config.hips_datasets[dataset]
        base_url = dataset_config.url
        hips_paths = dataset_config.paths

        return await self.build_hips_list_from_paths(
            base_url=base_url,
            hips_paths=hips_paths,
            client=client,
            logger=logger,
            config=config,
            dataset=dataset,
        )


hips_list_dependency = HiPSListDependency()
"""The dependency that caches the HiPS list for the default dataset."""

dataset_hips_list_dependency = DatasetHiPSListDependency()
"""The dependency that caches HiPS lists for individual datasets (v2 API)."""
