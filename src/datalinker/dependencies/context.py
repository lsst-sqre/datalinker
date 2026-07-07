"""Per-request context."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from lsst.daf.butler import LabeledButlerFactory
from rubin.repertoire import DiscoveryClient, discovery_dependency
from safir.dependencies.gafaelfawr import (
    auth_delegated_token_dependency,
    auth_logger_dependency,
)
from safir.metrics import EventManager
from structlog.stdlib import BoundLogger

from ..events import Events
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

    events: Events
    """Events publishers."""


class ContextDependency:
    """Provide a per-request context as a FastAPI dependency.

    Holds shared global state that is used for every request and uses it to
    create a new factory and request context for each request.
    """

    def __init__(self) -> None:
        self._butler_factory: LabeledButlerFactory | None = None
        self._events: Events | None = None

    async def initialize(self, event_manager: EventManager) -> None:
        """Initialize the process-wide shared context.

        Parameters
        ----------
        event_manager
            Global event manager.
        """
        self._events = Events()
        await self._events.initialize(event_manager)

    async def __call__(
        self,
        *,
        request: Request,
        discovery: Annotated[DiscoveryClient, Depends(discovery_dependency)],
        token: Annotated[str, Depends(auth_delegated_token_dependency)],
        logger: Annotated[BoundLogger, Depends(auth_logger_dependency)],
    ) -> RequestContext:
        if not self._events:
            raise RuntimeError("Context dependency not initialized")
        if not self._butler_factory:
            butler_repositories = await discovery.butler_repositories()
            self._butler_factory = LabeledButlerFactory(butler_repositories)
        bound_factory = self._butler_factory.bind(access_token=token)
        factory = Factory(bound_factory, discovery, logger)
        return RequestContext(
            request=request,
            factory=factory,
            logger=logger,
            events=self._events,
        )


context_dependency = ContextDependency()
"""The dependency that will return the per-request context."""
