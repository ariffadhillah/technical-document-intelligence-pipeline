from __future__ import annotations

from collections import defaultdict

from src.schemas.technical_knowledge import (
    ContactDetail,
    SourceEvidence,
    StructuredTechnicalDocument,
)
from src.validators.contact_normalizer import (
    ContactNormalizer,
)
from src.validators.models import (
    ContactValidationReport,
    ValidationIssue,
)


class ContactValidator:
    """
    Deterministic, non-mutating validator for extracted contacts.

    The validator checks whether important contact values are supported
    by their own evidence and reports suspicious duplication patterns.
    """

    CONTACT_FIELDS = (
        "email",
        "phone",
        "mobile",
        "fax",
        "website",
        "address",
    )

    def validate(
        self,
        document: StructuredTechnicalDocument,
    ) -> ContactValidationReport:
        issues: list[ValidationIssue] = []
        checked_field_count = 0

        for contact_index, contact in enumerate(
            document.contacts
        ):
            evidence_text = self._build_evidence_text(
                contact.evidence
            )

            for field_name in self.CONTACT_FIELDS:
                field_value = getattr(
                    contact,
                    field_name,
                )

                if not field_value:
                    continue

                checked_field_count += 1

                if not evidence_text:
                    issues.append(
                        ValidationIssue(
                            code="CONTACT_EVIDENCE_MISSING",
                            message=(
                                f"Contact field '{field_name}' has "
                                "a value but the contact contains no "
                                "searchable evidence."
                            ),
                            field_path=(
                                f"contacts.{contact_index}."
                                f"{field_name}"
                            ),
                            contact_index=contact_index,
                            evidence={
                                "value": field_value,
                            },
                        )
                    )
                    continue

                if not self._value_supported_by_evidence(
                    field_name=field_name,
                    field_value=field_value,
                    evidence_text=evidence_text,
                ):
                    issues.append(
                        ValidationIssue(
                            code="CONTACT_VALUE_NOT_IN_EVIDENCE",
                            message=(
                                f"Contact field '{field_name}' could "
                                "not be matched against its evidence."
                            ),
                            field_path=(
                                f"contacts.{contact_index}."
                                f"{field_name}"
                            ),
                            contact_index=contact_index,
                            evidence={
                                "value": field_value,
                                "organization": (
                                    contact.organization
                                ),
                                "person_name": (
                                    contact.person_name
                                ),
                            },
                        )
                    )

        issues.extend(
            self._find_suspicious_duplicate_contacts(
                document.contacts
            )
        )

        return ContactValidationReport(
            contact_count=len(document.contacts),
            checked_field_count=checked_field_count,
            issues=tuple(issues),
        )

    @staticmethod
    def _build_evidence_text(
        evidence_items: list[SourceEvidence],
    ) -> str:
        values: list[str] = []

        for evidence in evidence_items:
            for value in (
                evidence.quote,
                evidence.post_id,
                evidence.attachment_filename,
                evidence.source_url,
            ):
                if value:
                    values.append(value)

        return "\n".join(values)

    def _value_supported_by_evidence(
        self,
        *,
        field_name: str,
        field_value: str,
        evidence_text: str,
    ) -> bool:
        if field_name in {
            "phone",
            "mobile",
            "fax",
        }:
            return self._phone_supported_by_evidence(
                phone_value=field_value,
                evidence_text=evidence_text,
            )

        if field_name == "email":
            normalized_value = (
                ContactNormalizer.normalize_email(
                    field_value
                )
            )
        elif field_name == "website":
            normalized_value = (
                ContactNormalizer.normalize_website(
                    field_value
                )
            )
        else:
            normalized_value = (
                ContactNormalizer.normalize_text(
                    field_value
                )
            )

        normalized_evidence = (
            ContactNormalizer.normalize_text(
                evidence_text
            )
        )

        if (
            normalized_value is None
            or normalized_evidence is None
        ):
            return False

        return normalized_value in normalized_evidence

    @staticmethod
    def _phone_supported_by_evidence(
        *,
        phone_value: str,
        evidence_text: str,
    ) -> bool:
        normalized_phone = (
            ContactNormalizer.normalize_phone(
                phone_value
            )
        )
        normalized_evidence = (
            ContactNormalizer.normalize_phone(
                evidence_text
            )
        )

        if (
            normalized_phone is None
            or normalized_evidence is None
        ):
            return False

        if normalized_phone in normalized_evidence:
            return True

        minimum_suffix_length = 7

        if len(normalized_phone) < minimum_suffix_length:
            return False

        return (
            normalized_phone[-minimum_suffix_length:]
            in normalized_evidence
        )

    def _find_suspicious_duplicate_contacts(
        self,
        contacts: list[ContactDetail],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        phone_indexes: dict[str, list[int]] = defaultdict(
            list
        )

        for contact_index, contact in enumerate(contacts):
            for field_name in (
                "phone",
                "mobile",
            ):
                value = getattr(contact, field_name)

                normalized = (
                    ContactNormalizer.normalize_phone(
                        value
                    )
                )

                if normalized:
                    phone_indexes[normalized].append(
                        contact_index
                    )

        for normalized_phone, indexes in (
            phone_indexes.items()
        ):
            unique_indexes = sorted(set(indexes))

            if len(unique_indexes) < 2:
                continue

            contact_addresses = {
                ContactNormalizer.normalize_text(
                    contacts[index].address
                )
                for index in unique_indexes
                if contacts[index].address
            }

            contact_people = {
                ContactNormalizer.normalize_text(
                    contacts[index].person_name
                )
                for index in unique_indexes
                if contacts[index].person_name
            }

            # Repeated organization phone numbers can be valid. It becomes
            # suspicious when the same number is attached to multiple
            # distinct addresses or people.
            if (
                len(contact_addresses) <= 1
                and len(contact_people) <= 1
            ):
                continue

            issues.append(
                ValidationIssue(
                    code="SUSPICIOUS_SHARED_PHONE",
                    message=(
                        "The same normalized phone number appears "
                        "on multiple contacts with different "
                        "addresses or people."
                    ),
                    severity="warning",
                    evidence={
                        "normalized_phone": normalized_phone,
                        "contact_indexes": unique_indexes,
                    },
                )
            )

        return issues