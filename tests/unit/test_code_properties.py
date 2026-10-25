"""Property-based checks of short-code rules across generated inputs."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from shortlink.domain.codes import (
    ALPHABET,
    CODE_PATTERN,
    MAX_CODE_LENGTH,
    MIN_CODE_LENGTH,
    RESERVED_CODES,
    generate_code,
    validate_code,
)
from shortlink.domain.errors import InvalidCodeError

SERVABLE = st.text(
    alphabet=ALPHABET + "_-", min_size=MIN_CODE_LENGTH, max_size=MAX_CODE_LENGTH
).filter(lambda code: code not in RESERVED_CODES)


@given(st.integers(MIN_CODE_LENGTH, MAX_CODE_LENGTH))
def test_generated_codes_have_the_length_and_alphabet_requested(length: int) -> None:
    code = generate_code(length)
    assert len(code) == length
    assert set(code) <= set(ALPHABET)
    assert CODE_PATTERN.fullmatch(code)


@given(st.integers().filter(lambda n: not MIN_CODE_LENGTH <= n <= MAX_CODE_LENGTH))
def test_lengths_outside_the_supported_range_are_rejected(length: int) -> None:
    with pytest.raises(InvalidCodeError):
        generate_code(length)


@given(SERVABLE)
def test_every_servable_code_is_accepted(code: str) -> None:
    validate_code(code)


@given(st.text(min_size=1).filter(lambda code: not CODE_PATTERN.fullmatch(code)))
def test_codes_outside_the_pattern_are_rejected(code: str) -> None:
    with pytest.raises(InvalidCodeError):
        validate_code(code)


@pytest.mark.parametrize("code", sorted(RESERVED_CODES))
def test_route_names_are_reserved(code: str) -> None:
    with pytest.raises(InvalidCodeError):
        validate_code(code)
