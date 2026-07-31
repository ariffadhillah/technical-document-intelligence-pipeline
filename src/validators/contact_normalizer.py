from __future__ import annotations

import re


class ContactNormalizer:
    """
    Deterministic normalization utilities used only for comparison.

    Original contact values are never modified. These normalized values
    help compare different formatting styles such as:

        +41(0)41 269 00 00
        +41 41 269 00 00
        041 269 00 00
    """

    _WHITESPACE_PATTERN = re.compile(r"\s+")
    _NON_DIGIT_PATTERN = re.compile(r"\D+")

    @classmethod
    def normalize_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = cls._WHITESPACE_PATTERN.sub(
            " ",
            value,
        ).strip()

        return normalized.casefold() or None

    @classmethod
    def normalize_email(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip().casefold()
        return normalized or None

    @classmethod
    def normalize_website(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip().casefold()

        for prefix in (
            "https://",
            "http://",
        ):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break

        normalized = normalized.rstrip("/")

        if normalized.startswith("www."):
            normalized = normalized[4:]

        return normalized or None

    @classmethod
    def normalize_phone(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Return a comparison-only phone representation.

        The optional trunk marker ``(0)`` is removed when it follows an
        international country code. No country-specific conversion is
        performed because the source country may be unknown.
        """

        if value is None:
            return None

        compact = value.strip()

        compact = re.sub(
            r"(\+\d{1,3})\s*\(0\)",
            r"\1",
            compact,
        )

        digits = cls._NON_DIGIT_PATTERN.sub(
            "",
            compact,
        )

        if not digits:
            return None

        return digits

    @classmethod
    def equivalent_phone(
        cls,
        first: str | None,
        second: str | None,
    ) -> bool:
        first_normalized = cls.normalize_phone(first)
        second_normalized = cls.normalize_phone(second)

        if (
            first_normalized is None
            or second_normalized is None
        ):
            return False

        if first_normalized == second_normalized:
            return True

        # Local and international forms can differ by country/trunk prefix.
        # Comparing a sufficiently long suffix catches common representations
        # while reducing accidental matches between short extensions.
        minimum_suffix_length = 7

        if (
            len(first_normalized) >= minimum_suffix_length
            and len(second_normalized) >= minimum_suffix_length
        ):
            return (
                first_normalized.endswith(second_normalized)
                or second_normalized.endswith(first_normalized)
            )

        return False