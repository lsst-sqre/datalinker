"""Template management.

Provides a shared Jinja template environment used for generating templated
responses.
"""

from __future__ import annotations

from fastapi.templating import Jinja2Templates
from jinja2 import Environment, PackageLoader, StrictUndefined

__all__ = ["templates"]

templates = Jinja2Templates(
    env=Environment(
        loader=PackageLoader("datalinker", "templates"),
        undefined=StrictUndefined,
        autoescape=True,
    )
)
"""FastAPI renderer for templated responses."""
