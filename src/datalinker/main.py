"""The main application factory for the datalinker service.

Notes
-----
Be aware that, following the normal pattern for FastAPI services, the app is
constructed when this module is loaded and is not deferred until a function is
called.
"""

from __future__ import annotations

from importlib.metadata import metadata, version

import structlog
from fastapi import FastAPI
from safir.fastapi import ClientRequestError, client_request_error_handler
from safir.logging import Profile, configure_logging, configure_uvicorn_logging
from safir.middleware.ivoa import CaseInsensitiveQueryMiddleware
from safir.middleware.x_forwarded import XForwardedMiddleware
from safir.sentry import initialize_sentry
from safir.slack.webhook import SlackRouteErrorHandler

from . import __version__
from .config import config
from .handlers.external import external_router
from .handlers.internal import internal_router

__all__ = ["app"]

initialize_sentry(release=__version__)

app = FastAPI(
    title="datalinker",
    description=metadata("datalinker")["Summary"],
    version=version("datalinker"),
    openapi_url=f"{config.path_prefix}/openapi.json",
    docs_url=f"{config.path_prefix}/docs",
    redoc_url=f"{config.path_prefix}/redoc",
)
"""The main FastAPI application for datalinker."""

# Configure logging.
configure_logging(
    profile=config.log_profile, log_level=config.log_level, name="datalinker"
)
if config.log_profile == Profile.production:
    configure_uvicorn_logging(config.log_level)

# Attach the routers.
app.include_router(internal_router)
app.include_router(external_router, prefix=config.path_prefix)

# Add the middleware.
app.add_middleware(CaseInsensitiveQueryMiddleware)
app.add_middleware(XForwardedMiddleware)

# Add exception handlers.
app.exception_handler(ClientRequestError)(client_request_error_handler)

# Configure Slack alerts.
if config.slack_webhook:
    webhook = config.slack_webhook
    logger = structlog.get_logger(__name__)
    SlackRouteErrorHandler.initialize(webhook, config.name, logger)
    logger.debug("Initialized Slack webhook")
