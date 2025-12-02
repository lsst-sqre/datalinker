"""Per-request context."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from lsst.daf.butler import LabeledButlerFactory
from rubin.repertoire import DiscoveryClient, discovery_dependency
from safir.dependencies.gafaelfawr import auth_delegated_token_dependency
from safir.dependencies.logger import logger_dependency
from structlog.stdlib import BoundLogger

from ..factory import Factory

__all__ = [
    "ContextDependency",
    "RequestContext",
    "context_dependency",
]


@dataclass(slots=True)
class RequestContext:
    """Holds per-request context, such as the factory."""

    request: Request
    """Incoming request."""

    factory: Factory
    """Component factory."""

    logger: BoundLogger
    """Per-request logger."""


class ContextDependency:
    """Provide a per-request context as a FastAPI dependency.

    Holds shared global state that is used for every request and uses it to
    create a new factory and request context for each request.
    """

    def __init__(self) -> None:
        self._butler_factory = LabeledButlerFactory()

    async def __call__(
        self,
        *,
        request: Request,
        discovery: Annotated[DiscoveryClient, Depends(discovery_dependency)],
        delegated_token: Annotated[
            str, Depends(auth_delegated_token_dependency)
        ],
        logger: Annotated[BoundLogger, Depends(logger_dependency)],
    ) -> RequestContext:
        bound_factory = self._butler_factory.bind(access_token=delegated_token)
        factory = Factory(bound_factory, discovery, logger)
        return RequestContext(request=request, factory=factory, logger=logger)


context_dependency = ContextDependency()
"""The dependency that will return the per-request context."""
