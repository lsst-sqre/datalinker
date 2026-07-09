"""Exceptions for datalinker."""

from safir.fastapi import ClientRequestError

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


class IdentifierMalformedError(Exception):
    """An identifier could not be parsed."""

    def __init__(self, id: str) -> None:
        super().__init__(f"Unable to extract valid dataset ID from '{id}'")


class IdentifierNotFoundError(Exception):
    """No dataset found for this identifier."""

    def __init__(self, id: str) -> None:
        super().__init__(f"Unknown dataset ID '{id}'")
