"""Generate unpredictable base62 codes and validate custom codes."""

import re
import secrets
import string

from shortlink.domain.errors import InvalidCodeError

ALPHABET = string.ascii_letters + string.digits
CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{4,32}$")
RESERVED_CODES = frozenset({"health", "docs", "redoc", "links"})
MIN_CODE_LENGTH = 4
MAX_CODE_LENGTH = 32


def validate_code(code: str) -> None:
    """Reject malformed and reserved short codes.

    Args:
        code: Candidate code to validate.

    Raises:
        InvalidCodeError: If the code cannot be served as a link.
    """
    if not CODE_PATTERN.fullmatch(code) or code in RESERVED_CODES:
        raise InvalidCodeError


def generate_code(length: int) -> str:
    """Generate a cryptographically random base62 code.

    Args:
        length: Number of characters, between 4 and 32.

    Returns:
        The generated code.

    Raises:
        InvalidCodeError: If the configured length is outside the supported range.
    """
    if not MIN_CODE_LENGTH <= length <= MAX_CODE_LENGTH:
        raise InvalidCodeError
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
