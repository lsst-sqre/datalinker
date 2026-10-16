"""Exceptions for datalinker."""

from fastapi import status
from safir.fastapi import ClientRequestError
from safir.models import ErrorLocation

__all__ = [
    "ButlerError",
    "ButlerUriNotSignedError",
    "IdentifierError",
    "IdentifierMalformedError",
    "IdentifierNotFoundError",
]


class ButlerError(Exception):
    """Error in parsing the results of a Butler call."""


class ButlerUriNotSignedError(ButlerError):
    """An image URL returned from the Butler was not signed."""

    def __init__(self, url: str) -> None:
        super().__init__(f"Image URL {url} from Butler server was not signed")


class IdentifierError(ClientRequestError):
    """Invalid identifier."""


class IdentifierMalformedError(IdentifierError):
    """An identifier could not be parsed."""

    error = "malformed_ivoid"

    def __init__(self, id: str) -> None:
        super().__init__(f"Unable to extract valid dataset ID from '{id}'")


class IdentifierNotFoundError(IdentifierError):
    """No dataset found for this identifier."""

    error = "ivoid_not_found"
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(
        self,
        id: str,
        location: ErrorLocation | None = None,
        field_path: list[str] | None = None,
    ) -> None:
        super().__init__(f"Unknown dataset ID '{id}'", location, field_path)
