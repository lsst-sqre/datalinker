"""Generate a DataLink response for an identifier."""

from contextlib import suppress

from lsst.daf.butler import Butler, LabeledButlerFactoryProtocol
from rubin.repertoire import DiscoveryClient
from structlog.stdlib import BoundLogger

from ..exceptions import (
    ButlerUriNotSignedError,
    IdentifierMalformedError,
    IdentifierNotFoundError,
)
from ..models import DataLinkError, DataLinkRow

__all__ = ["LinksService"]


class LinksService:
    """Generate a DataLink response for an identifier.

    Looks up an identifier in the Butler to get a signed URL for the image and
    generates the rqeuired information for a DataLink response.

    Parameters
    ----------
    butler_factory
        Factory to create Butler clients.
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

    def build_datalink(self, ids: list[str]) -> list[DataLinkRow]:
        """Return the DataLink information for given identifiers.

        Both this method and the handler method that calls it must not be
        async functions since the underlying Butler client is not async and
        FastAPI must be forced to run the handler in a thread pool. This
        method should therefore be run from a separate dependency that is
        declared as sync, and then the results of that dependency can be used
        in the main async handler.

        Parameters
        ----------
        ids
            Identifiers to look up.

        Returns
        -------
        list of DataLinkRow
            List of either DataLink results or an error, suitable for passing
            to the records parameter of the Jinja template.
        """
        results = []
        for id in ids:
            try:
                results.append(self._get_datalink_for_id(id))
            except IdentifierMalformedError as e:
                error = DataLinkRow.from_error(id, DataLinkError.USAGE, e)
                results.append(error)
            except IdentifierNotFoundError as e:
                error = DataLinkRow.from_error(id, DataLinkError.NOT_FOUND, e)
                results.append(error)
        return results

    async def get_cutout_sync_url(self, ids: list[str]) -> str | None:
        """Get sync URL to SODA service for cutouts, if one exists.

        Currently, this uses the first valid ID in the list sent by the user
        to determine the cutout URLs, even if there are IDs from different
        data releases. This is not semantically correct since the cutout
        service may have a different base URL for different data releases, but
        currently Rubin uses a single cutout service so live with that problem
        for now.

        Parameters
        ----------
        ids
            List of identifiers requested by the user.

        Returns
        -------
        str or None
            URL to the sync SODA service for performing cutouts, or `None` if
            none is available.
        """
        parsed_uri = None
        for id in ids:
            with suppress(Exception):
                parsed_uri = Butler.parse_dataset_uri(id)
                break
        if not parsed_uri:
            return None
        return await self._discovery.url_for_data(
            "cutout", parsed_uri.label, version="soda-sync-1.0"
        )

    def _get_datalink_for_id(self, id: str) -> DataLinkRow:
        """Get the DataLink information for a single identifier.

        Parameters
        ----------
        id
            Identifier to an image.

        Returns
        -------
        DataLinkRow
            Information to construct a result row.

        Raises
        ------
        ButlerUriNotSignedError
            Raised if the URL returned by Butler is not signed.
        IdentifierMalformedError
            Raised if the identifier could not be parsed.
        IdentifierNotFoundError
            Raised if no dataset is found for the provided identifier.
        """
        logger = self._logger.bind(id=id)
        factory = self._butler_factory

        try:
            dataset = Butler.get_dataset_from_uri(id, factory=factory)
        except FileNotFoundError as e:
            # Invalid Butler labels will cause it to fall back to trying to
            # read a local Butler config and thus throw FileNotFoundError.
            logger.warning("Repository for identifier does not exist")
            raise IdentifierNotFoundError(id) from e
        except LookupError as e:
            logger.warning("Unknown dataset ID")
            raise IdentifierNotFoundError(id) from e
        except ValueError as e:
            logger.warning("Unable to parse dataset ID")
            raise IdentifierMalformedError(id) from e

        butler = dataset.butler
        ref = dataset.dataset
        if not ref:
            logger.warning("Dataset does not exist", label=str(butler))
            raise IdentifierNotFoundError(id)

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

        # Return the DataLink model.
        return DataLinkRow(
            id=id,
            error=None,
            image_url=str(image_uri),
            image_size=image_uri.size(),
            is_raw=ref.datasetType.name == "raw",
        )
