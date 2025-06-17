"""The main application factory for the datalinker service.

Notes
-----
Be aware that, following the normal pattern for FastAPI services, the app is
constructed when this module is loaded and is not deferred until a function is
called.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import metadata, version

import structlog
from fastapi import FastAPI
from safir.dependencies.http_client import http_client_dependency
from safir.logging import Profile, configure_logging, configure_uvicorn_logging
from safir.middleware.ivoa import CaseInsensitiveQueryMiddleware
from safir.middleware.x_forwarded import XForwardedMiddleware
from safir.slack.webhook import SlackRouteErrorHandler

from .dependencies.config import config_dependency
from .handlers.external import external_router
from .handlers.hips import hips_router, hips_v2_router
from .handlers.internal import internal_router

__all__ = ["app"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Set up and tear down the application."""
    yield

    await http_client_dependency.aclose()


config = config_dependency.config()

configure_logging(
    profile=config.profile, log_level=config.log_level, name="datalinker"
)
if config.profile == Profile.production:
    configure_uvicorn_logging(config.log_level)

app = FastAPI(
    title="datalinker",
    description=metadata("datalinker")["Summary"],
    version=version("datalinker"),
    openapi_url=f"{config.path_prefix}/openapi.json",
    docs_url=f"{config.path_prefix}/docs",
    redoc_url=f"{config.path_prefix}/redoc",
    lifespan=lifespan,
)
"""The main FastAPI application for datalinker."""

# Attach the routers.
app.include_router(internal_router)
app.include_router(external_router, prefix=config.path_prefix)
app.include_router(hips_router, prefix=config.hips_path_prefix)
app.include_router(hips_v2_router, prefix=config.hips_v2_path_prefix)

# Add the middleware.
app.add_middleware(CaseInsensitiveQueryMiddleware)
app.add_middleware(XForwardedMiddleware)

# Configure Slack alerts.
if config.slack_webhook:
    webhook = config.slack_webhook
    logger = structlog.get_logger(__name__)
    SlackRouteErrorHandler.initialize(webhook, config.name, logger)
    logger.debug("Initialized Slack webhook")
