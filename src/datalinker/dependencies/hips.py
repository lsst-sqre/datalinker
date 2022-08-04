"""HiPS list cache."""

import re
from typing import Optional

from fastapi import Depends
from httpx import AsyncClient
from safir.dependencies.http_client import http_client_dependency
from safir.dependencies.logger import logger_dependency
from structlog.stdlib import BoundLogger

from ..config import config
from ..constants import HIPS_DATASETS

__all__ = [
    "HiPSListDependency",
    "hips_list_dependency",
]


class HiPSListDependency:
    """Maintain a cache of HiPS properties files for this deployment.

    A deployment of the Science Platform may have several trees of HiPS data
    served out of GCS.  Those need to be gathered together and served as a
    unified HiPS list of all available trees.  Rather than making multiple API
    calls to GCS each time this list is requested, cache the HiPS list
    constructed from the ``properties`` files and prefer to serve them from
    the cache.
    """

    def __init__(self) -> None:
        self._hips_list: Optional[str] = None

    async def __call__(
        self,
        client: AsyncClient = Depends(http_client_dependency),
        logger: BoundLogger = Depends(logger_dependency),
    ) -> str:
        if not self._hips_list:
            self._hips_list = await self._build_hips_list(client, logger)
        return self._hips_list

    async def _build_hips_list(
        self, client: AsyncClient, logger: BoundLogger
    ) -> str:
        """Retrieve and cache properties files for all HiPS data sets.

        Currently, this hard-codes the available lists.  This will eventually
        be moved to configuration.

        Parameters
        ----------
        client : `httpx.AsyncClient`
            Client to use to retrieve the HiPS lists.
        logger : `structlog.stdlib.BoundLogger`
            Logger for any error messages.
        """
        lists = []
        for dataset in HIPS_DATASETS:
            url = config.hips_base_url + f"/{dataset}"
            r = await client.get(
                url + "/properties",
                headers={"Authorization": f"bearer {config.token}"},
            )
            if r.status_code != 200:
                logger.warning(
                    "Unable to get HiPS list",
                    url=url,
                    status=r.status_code,
                    error=r.reason_phrase,
                )
                continue
            data = r.text

            # Our HiPS properties files don't contain the URL
            # (hips_service_url), but this is mandatory in the entries in the
            # HiPS list.  Add it before hips_status.
            service_url = "{:25}= {}".format("hips_service_url", url)
            data = re.sub(
                "^hips_status",
                f"{service_url}\nhips_status",
                r.text,
                flags=re.MULTILINE,
            )
            lists.append(data)

        # The HiPS list is the concatenation of all the properties files
        # separated by blank lines.
        return "\n\n".join(lists)


hips_list_dependency = HiPSListDependency()
"""The dependency that caches the HiPS list."""
