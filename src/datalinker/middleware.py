"""Middleware for datalinker service."""

from typing import Awaitable, Callable
from urllib.parse import urlencode

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class CaseInsensitiveQueryMiddleware(BaseHTTPMiddleware):
    """Make query parameter keys all lowercase.

    Unfortunately, datalink requires that query parameters be case-insensitive,
    which is not supported by modern HTTP web frameworks.  This middleware
    attempts to work around this by lowercasing the query parameter keys
    before the request is processed, allowing normal FastAPI query parsing to
    then work without regard for case.  This, in turn, permits FastAPI to
    perform input validation on GET parameters, which would otherwise only
    happen if the case used in the request happened to match the case used in
    the function signature.

    Based on `fastapi#826 https://github.com/tiangolo/fastapi/issues/826`__.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        params = [(k.lower(), v) for k, v in request.query_params.items()]
        request.scope["query_string"] = urlencode(params).encode()
        return await call_next(request)
