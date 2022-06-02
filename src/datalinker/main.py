"""The main application factory for the datalinker service.

Notes
-----
Be aware that, following the normal pattern for FastAPI services, the app is
constructed when this module is loaded and is not deferred until a function is
called.
"""

from importlib.metadata import metadata, version

from fastapi import FastAPI
from safir.dependencies.http_client import http_client_dependency
from safir.logging import configure_logging
from safir.middleware.ivoa import CaseInsensitiveQueryMiddleware
from safir.middleware.x_forwarded import XForwardedMiddleware

from .config import config
from .handlers.external import external_router
from .handlers.internal import internal_router

__all__ = ["app", "config"]


configure_logging(
    profile=config.profile,
    log_level=config.log_level,
    name=config.logger_name,
)

app = FastAPI(
    title="datalinker",
    description=metadata("datalinker")["Summary"],
    version=version("datalinker"),
    openapi_url="/api/datalink/openapi.json",
    docs_url="/api/datalink/docs",
    redoc_url="/api/datalink/redoc",
)
"""The main FastAPI application for datalinker."""

# Attach the routers.
app.include_router(internal_router)
app.include_router(external_router, prefix="/api/datalink")

# Add the middleware.
app.add_middleware(CaseInsensitiveQueryMiddleware)
app.add_middleware(XForwardedMiddleware)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await http_client_dependency.aclose()
