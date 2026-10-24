"""Domain failures translated to HTTP at the API boundary."""


class ShortlinkError(Exception):
    """Base class for expected application failures."""


class LinkNotFoundError(ShortlinkError):
    """The requested link does not exist."""


class LinkExpiredError(ShortlinkError):
    """The link has reached its expiry time."""


class CodeTakenError(ShortlinkError):
    """The code already belongs to another link."""


class InvalidCodeError(ShortlinkError):
    """The code is malformed or reserved by an application route."""


class InvalidExpiryError(ShortlinkError):
    """The expiry is not a timezone-aware future instant."""
