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
from safir.middleware.x_forwarded import XForwardedMiddleware

from .config import config
from .handlers.external import external_router
from .handlers.internal import internal_router
from .middleware import CaseInsensitiveQueryMiddleware

__all__ = ["app", "config"]


configure_logging(
    profile=config.profile,
    log_level=config.log_level,
    name=config.logger_name,
)

app = FastAPI()
"""The main FastAPI application for datalinker."""

# Define the external routes in a subapp so that it will serve its own OpenAPI
# interface definition and documentation URLs under the external URL.
_subapp = FastAPI(
    title="datalinker",
    description=metadata("datalinker")["Summary"],
    version=version("datalinker"),
)
_subapp.include_router(external_router)

# Attach the internal routes and subapp to the main application.
app.include_router(internal_router)
app.mount("/api/datalink/", _subapp)


@app.on_event("startup")
async def startup_event() -> None:
    app.add_middleware(XForwardedMiddleware)
    app.add_middleware(CaseInsensitiveQueryMiddleware)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await http_client_dependency.aclose()
