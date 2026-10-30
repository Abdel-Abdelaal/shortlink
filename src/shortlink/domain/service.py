"""Link creation, resolution and expiry policies."""

from datetime import datetime

from shortlink.domain.codes import generate_code, validate_code
from shortlink.domain.errors import (
    CodeTakenError,
    InvalidCodeError,
    InvalidExpiryError,
    LinkExpiredError,
)
from shortlink.domain.models import Link
from shortlink.domain.ports import Clock, LinkRepository

MAX_CODE_ATTEMPTS = 5


class LinkService:
    """Coordinate link policy through storage and clock ports."""

    def __init__(
        self, repository: LinkRepository, clock: Clock, code_length: int = 7
    ) -> None:
        """Bind the service to its adapters and generated-code length."""
        self._repository = repository
        self._clock = clock
        self._code_length = code_length

    def create(
        self,
        target_url: str,
        code: str | None = None,
        expires_at: datetime | None = None,
    ) -> Link:
        """Store a new link with a custom or generated code.

        Args:
            target_url: Validated HTTP or HTTPS redirect destination.
            code: Optional user-selected code.
            expires_at: Optional timezone-aware future expiry time.

        Returns:
            The newly persisted link.

        Raises:
            InvalidExpiryError: If expiry is naive or not in the future.
            InvalidCodeError: If a custom code is malformed or reserved.
            CodeTakenError: If a custom code is occupied or retries are exhausted.
        """
        created_at = self._clock.now()
        if expires_at is not None and (
            expires_at.tzinfo is None or expires_at <= created_at
        ):
            raise InvalidExpiryError
        if code is not None:
            validate_code(code)
            return self._store(code, target_url, created_at, expires_at)
        for _ in range(MAX_CODE_ATTEMPTS):
            candidate = generate_code(self._code_length)
            try:
                validate_code(candidate)
            except InvalidCodeError:
                continue
            try:
                return self._store(candidate, target_url, created_at, expires_at)
            except CodeTakenError:
                continue
        raise CodeTakenError

    def inspect(self, code: str) -> Link:
        """Validate that a stored link is active without counting a redirect.

        Args:
            code: Short code to inspect.

        Returns:
            The stored link.

        Raises:
            LinkExpiredError: If the expiry boundary has been reached.
            LinkNotFoundError: If the code has no stored link.
        """
        link = self._repository.get(code)
        if link.expires_at is not None and link.expires_at <= self._clock.now():
            raise LinkExpiredError
        return link

    def resolve(self, code: str) -> Link:
        """Resolve an active link and count exactly one successful redirect.

        Args:
            code: Short code to resolve.

        Returns:
            The link before its hit count increment.

        Raises:
            LinkExpiredError: If the expiry boundary has been reached.
            LinkNotFoundError: If the code has no stored link.
        """
        link = self.inspect(code)
        self._repository.increment_hits(code)
        return link

    def stats(self, code: str) -> Link:
        """Fetch metadata without counting a redirect or rejecting expired links."""
        return self._repository.get(code)

    def delete(self, code: str) -> None:
        """Delete a stored link or raise LinkNotFoundError."""
        self._repository.delete(code)

    def _store(
        self,
        code: str,
        target_url: str,
        created_at: datetime,
        expires_at: datetime | None,
    ) -> Link:
        """Construct a link and persist it through the repository port."""
        link = Link(code, target_url, created_at, expires_at)
        self._repository.add(link)
        return link
