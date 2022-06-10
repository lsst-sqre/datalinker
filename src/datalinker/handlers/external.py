"""Handlers for the app's external root, ``/datalinker/``."""

from datetime import timedelta
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from google.cloud import storage
from lsst.daf import butler
from safir.dependencies.logger import logger_dependency
from safir.metadata import get_metadata
from structlog.stdlib import BoundLogger

from ..config import config
from ..models import Index

external_router = APIRouter()
"""FastAPI router for all external handlers."""

_BUTLER_CACHE: Dict[str, butler.Butler] = {}
"""Cache of Butlers by label."""

_TEMPLATES = Jinja2Templates(
    directory=str(Path(__file__).parent.parent / "templates")
)
"""FastAPI renderer for templated responses."""

__all__ = ["get_index", "external_router"]


def _get_butler(label: str) -> butler.Butler:
    """Retrieve a cached Butler object or create a new one.

    Don't bother adding a lock in, it's fine to make a couple if there's a
    race condition, they'll get cleaned up.

    Parameters
    ----------
    label : `str`
        Label identifying the Butler repository.

    Returns
    -------
    butler : `lsst.daf.butler.Butler`
        Corresponding Butler.
    """
    global _BUTLER_CACHE

    if label not in _BUTLER_CACHE:
        _BUTLER_CACHE[label] = butler.Butler(label)
    return _BUTLER_CACHE[label]


@external_router.get(
    "/",
    response_model=Index,
    response_model_exclude_none=True,
    summary="Application metadata",
)
async def get_index(
    logger: BoundLogger = Depends(logger_dependency),
) -> Index:
    """GET ``/datalinker/`` (the app's external root).

    By convention, the root of the external API includes a field called
    ``metadata`` that provides the same Safir-generated metadata as the
    internal root endpoint.
    """
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


@external_router.get(
    "/links",
    responses={404: {"description": "Specified identifier not found"}},
    summary="DataLink links for object",
)
def links(
    id: str,
    request: Request,
    logger: BoundLogger = Depends(logger_dependency),
) -> Response:
    # Parse the "butler://label/uuid" ID URI
    butler_uri = urlparse(id)
    label = butler_uri.netloc
    uuid = butler_uri.path[1:]
    logger.debug(f"Loading {label} {uuid}")

    # This returns lsst.resources.ResourcePath
    butler = _get_butler(label)
    ref = butler.registry.getDataset(UUID(uuid))
    if not ref:
        logger.warning("Dataset does not exist", id=id)
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["query", "id"],
                    "msg": f"Dataset {id} does not exist",
                    "type": "not_found",
                }
            ],
        )
    image_uri = butler.datastore.getURI(ref)
    logger.debug(f"Image URI is: {image_uri}")

    # Generate signed URL.
    image_uri_parts = urlparse(str(image_uri))
    storage_client = storage.Client()
    bucket = storage_client.bucket(image_uri_parts.netloc)
    blob = bucket.blob(image_uri_parts.path[1:])

    signed_url = blob.generate_signed_url(
        version="v4",
        # This URL is valid for one hour.
        expiration=timedelta(hours=1),
        # Allow only GET requests using this URL.
        method="GET",
    )

    return _TEMPLATES.TemplateResponse(
        "links.xml",
        {
            "id": id,
            "image_url": signed_url,
            "image_size": image_uri.size(),
            "cutout_url": config.cutout_url,
            "request": request,
        },
        media_type="application/x-votable+xml",
    )
