"""Component factory for datalinker."""

from __future__ import annotations

from lsst.daf.butler import LabeledButlerFactoryProtocol
from rubin.repertoire import DiscoveryClient
from structlog.stdlib import BoundLogger

from .services.links import LinksService

__all__ = ["Factory"]


class Factory:
    """Component factory for datalinker.

    Parameters
    ----------
    butler_factory
        Shared labeled Butler factory.
    discovery_client
        Service discovery client.
    logger
        Logger to use.
    """

    def __init__(
        self,
        butler_factory: LabeledButlerFactoryProtocol,
        discovery_client: DiscoveryClient,
        logger: BoundLogger,
    ) -> None:
        self._butler_factory = butler_factory
        self._discovery = discovery_client
        self._logger = logger

    def create_links_service(self) -> LinksService:
        """Create a service for generating the DataLink response."""
        return LinksService(
            self._butler_factory, self._discovery, self._logger
        )
