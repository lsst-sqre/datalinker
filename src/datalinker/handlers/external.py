"""Handlers for the app's external root, ``/datalinker/``."""

from datetime import timedelta
from io import BytesIO
from typing import Dict, Generator
from urllib.parse import urlparse
from uuid import UUID

from astropy.io.votable.tree import Field, Resource, Table, VOTableFile
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, StreamingResponse
from google.cloud import storage
from lsst.daf.butler import Butler
from safir.dependencies.logger import logger_dependency
from safir.metadata import get_metadata
from structlog.stdlib import BoundLogger

from ..config import config
from ..models import Index

__all__ = ["get_index", "external_router"]

external_router = APIRouter()
"""FastAPI router for all external handlers."""


@external_router.get(
    "/",
    description=(
        "Document the top-level API here. By default it only returns metadata"
        " about the application."
    ),
    response_model=Index,
    response_model_exclude_none=True,
    summary="Application metadata",
)
async def get_index(
    logger: BoundLogger = Depends(logger_dependency),
) -> Index:
    """GET ``/datalinker/`` (the app's external root).

    Customize this handler to return whatever the top-level resource of your
    application should return. For example, consider listing key API URLs.
    When doing so, also change or customize the response model in
    `datalinker.models.Index`.

    By convention, the root of the external API includes a field called
    ``metadata`` that provides the same Safir-generated metadata as the
    internal root endpoint.
    """
    # There is no need to log simple requests since uvicorn will do this
    # automatically, but this is included as an example of how to use the
    # logger for more complex logging.
    logger.info("Request for application metadata")

    metadata = get_metadata(
        package_name="datalinker",
        application_name=config.name,
    )
    return Index(metadata=metadata)


@external_router.get("/cone_search", response_class=RedirectResponse)
async def cone_search(
    table: str,
    ra_col: str,
    dec_col: str,
    ra_val: str,
    dec_val: str,
    radius: str,
    logger: BoundLogger = Depends(logger_dependency),
) -> str:

    url = (
        "/api/tap/sync?LANG=ADQL&REQUEST=doQuery"
        + f"&QUERY=SELECT+*+FROM+{table}+WHERE+CONTAINS("
        + f"POINT('ICRS',{ra_col},{dec_col}),"
        + f"CIRCLE('ICRS',{ra_val},{dec_val},{radius})"
        + ")=1"
    )

    logger.info(f"Redirecting to {url}")
    return url


_butler_cache: Dict[str, Butler] = dict()


def retrieve_butler(label: str) -> Butler:
    # Best effort to cache butler objects.
    # Don't bother adding a lock in, it's fine to make
    # a couple if there's a race condition, they'll get
    # cleaned up.
    if label in _butler_cache:
        return _butler_cache[label]

    b = Butler(label)
    _butler_cache[label] = b
    return b


@external_router.get("/links", response_class=StreamingResponse)
async def links(
    id: str,
    logger: BoundLogger = Depends(logger_dependency),
) -> StreamingResponse:
    # Parse the "butler://label/uuid" ID URI
    butler_uri = urlparse(id)
    label = butler_uri.netloc
    uuid_str = butler_uri.path[1:]
    logger.info(f"Loading {label} {uuid_str}")

    uuid = UUID(uuid_str)
    butler = retrieve_butler(label)

    # This returns lsst.resources.ResourcePath
    ref = butler.registry.getDataset(uuid)
    if not ref:
        logger.error("Dataset does not exist")
        image_uri = None
    else:
        image_uri = butler.datastore.getURI(ref)

    logger.info(f"Image_uri is: {image_uri}")

    votable = VOTableFile()
    resource = Resource()
    table = Table(
        votable, descriptions=f"Links table for observation dataset {id}"
    )

    votable.resources.append(resource)
    resource.tables.append(table)

    table.fields.extend(
        [
            Field(
                votable,
                ID="ID",
                datatype="char",
                arraysize="*",
                ucd="meta.id;meta.main",
            ),
            Field(
                votable,
                ID="access_url",
                datatype="char",
                arraysize="*",
                ucd="meta.ref.url",
            ),
            Field(
                votable,
                ID="service_def",
                datatype="char",
                arraysize="*",
                ucd="meta.ref",
            ),
            Field(
                votable,
                ID="error_message",
                datatype="char",
                arraysize="*",
                ucd="meta.code.error",
            ),
            Field(
                votable,
                ID="description",
                datatype="char",
                arraysize="*",
                ucd="meta.note",
            ),
            Field(
                votable,
                ID="semantics",
                datatype="char",
                arraysize="*",
                ucd="meta.code",
            ),
            Field(
                votable,
                ID="content_type",
                datatype="char",
                arraysize="*",
                ucd="meta.code.mime",
            ),
            Field(
                votable,
                ID="content_length",
                datatype="long",
                arraysize="1",
                ucd="phys.size;meta.file",
                unit="byte",
            ),
        ]
    )

    # Generate signed URL
    image_uri_parts = urlparse(str(image_uri))
    storage_client = storage.Client()
    bucket = storage_client.bucket(image_uri_parts.netloc)
    blob = bucket.blob(image_uri_parts.path[1:])

    signed_url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for one hour.
        expiration=timedelta(hours=1),
        # Allow GET requests using this URL.
        method="GET",
    )

    image_size = 0
    if image_uri:
        image_size = image_uri.size()

    table.create_arrays(1)
    table.array[0] = (
        id,
        signed_url,
        "",
        "",
        "Primary image or observation data file",
        "#this",
        "application/fits",
        image_size,
    )

    def iter_result() -> Generator:
        with BytesIO() as fd:
            votable.to_xml(fd)
            fd.seek(0)
            yield from fd

    return StreamingResponse(
        iter_result(), media_type="application/x-votable+xml"
    )
