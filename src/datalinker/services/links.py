"""Generate a DataLink response for an identifier."""

from __future__ import annotations

from lsst.daf.butler import Butler, LabeledButlerFactoryProtocol
from rubin.repertoire import DiscoveryClient
from structlog.stdlib import BoundLogger

from ..exceptions import (
    ButlerUriNotSignedError,
    IdentifierMalformedError,
    IdentifierNotFoundError,
)
from ..models import DataLink

__all__ = ["LinksService"]


class LinksService:
    """Generate a DataLink response for an identifier.

    Looks up an identifier in the Butler to get a signed URL for the image and
    generates the DataLink response, including any appropriate additional
    descriptors based on service discovery responses.

    Parameters
    ----------
    butler_factory
        Factory to create Butler clients.
    discovery_client
        Service discovery client.
    logger
        Logger to use.

    Raises
    ------
    ButlerError
        Raised if there was some failure parsing the Butler results.
    IdentifierMalformedError
        Raised if the identifier could not be parsed.
    IdentifierNotFoundError
        Raised if no dataset is found for the provided identifier.
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

    def build_datalink(self, id: str, cutout_sync_url: str | None) -> DataLink:
        """Return the DataLink information for a given identifier.

        Both this method and the handler method that calls it must not be
        async functions since the underlying Butler client is not async and
        FastAPI must be forced to run the handler in a thread pool. This means
        that, before calling this function, a separate async FastAPI
        dependency should call `get_cutout_sync_url` and pass that result into
        the non-async handler, which in turn should pass that into this
        function.

        Parameters
        ----------
        id
            Identifier to look up.
        cutout_sync_url
            URL to the SODA sync service for making cutouts, if any. This
            should be obtained by calling `get_cutout_sync_url` first.
        """
        logger = self._logger.bind(id=id)
        factory = self._butler_factory

        try:
            dataset = Butler.get_dataset_from_uri(id, factory=factory)
        except FileNotFoundError as e:
            # Invalid Butler labels will cause it to fall back to trying to
            # read a local Butler config.
            msg = f"Repository for {id} does not exist"
            logger.warning(msg)
            raise IdentifierNotFoundError(msg) from e
        except ValueError as e:
            # Bad or missing UUID in URI.
            msg = "Unable to extract valid dataset ID from {id}"
            logger.warning(msg)
            raise IdentifierMalformedError(msg) from e

        butler = dataset.butler
        ref = dataset.dataset
        if not ref:
            logger.warning("Dataset does not exist", label=str(butler))
            raise IdentifierNotFoundError(f"Dataset {id} does not exist")

        # Get an lsst.resources.ResourcePath for the identifier.
        logger.debug(
            "Retrieving object from Butler",
            butler=str(dataset.butler),
            uuid=str(dataset.dataset),
        )
        image_uri = butler.getURI(ref)
        logger = logger.bind(image_uri=image_uri)
        logger.debug("Got image URI from Butler")
        if image_uri.scheme not in ("https", "http"):
            raise ButlerUriNotSignedError(str(image_uri))

        # Generate the response. Suppress the cutout sync URL for raw images,
        # since cutouts are not supported for them currently.
        if ref.datasetType.name == "raw":
            cutout_sync_url = None
        return DataLink(
            id=id,
            image_url=str(image_uri),
            image_size=image_uri.size(),
            cutout_sync_url=cutout_sync_url,
        )

    async def get_cutout_sync_url(self, id: str) -> str | None:
        """Get sync URL to SODA service for cutouts, if one exists.

        Parameters
        ----------
        id
            Identifier that may be to an image supporting cutouts.

        Returns
        -------
        str or None
            URL to the sync SODA service for performing cutouts, or `None` if
            none is available.
        """
        try:
            parsed_uri = Butler.parse_dataset_uri(id)
        except Exception:
            return None
        return await self._discovery.url_for_data(
            "cutout", parsed_uri.label, version="soda-sync-1.0"
        )
