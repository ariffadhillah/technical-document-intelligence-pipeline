from src.schemas.technical_knowledge import (
    ContactDetail,
    SourceEvidence,
    StructuredTechnicalDocument,
)
from src.validators import ContactValidator


def build_document(
    contacts: list[ContactDetail],
) -> StructuredTechnicalDocument:
    return StructuredTechnicalDocument(
        document_id="thread_95",
        title="Nutzfahrzeug AG Zentralschweiz",
        summary="Workshop contact information.",
        contacts=contacts,
    )


def test_accepts_two_distinct_locations_and_phones() -> None:
    document = build_document(
        contacts=[
            ContactDetail(
                organization=(
                    "Nutzfahrzeug AG Zentralschweiz"
                ),
                phone="+41(0)41 666 77 00",
                address=(
                    "Allmendstrasse 2, "
                    "CH-6060 Sarnen, Switzerland"
                ),
                evidence=[
                    SourceEvidence(
                        evidence_type="forum_post",
                        post_id="498",
                        quote=(
                            "Nutzfahrzeug AG Zentralschweiz\n"
                            "Allmendstrasse 2\n"
                            "CH-6060 Sarnen\n"
                            "Tel. +41(0)41 666 77 00"
                        ),
                    )
                ],
            ),
            ContactDetail(
                organization=(
                    "Nutzfahrzeug AG Zentralschweiz"
                ),
                phone="+41(0)41 269 00 00",
                address=(
                    "Hasliring 18, "
                    "CH-6032 Emmen, Switzerland"
                ),
                evidence=[
                    SourceEvidence(
                        evidence_type="forum_post",
                        post_id="498",
                        quote=(
                            "Nutzfahrzeug AG Zentralschweiz\n"
                            "Hasliring 18\n"
                            "CH-6032 Emmen\n"
                            "Tel. +41(0)41 269 00 00"
                        ),
                    )
                ],
            ),
        ]
    )

    report = ContactValidator().validate(document)

    assert report.error_count == 0
    assert not any(
        issue.code == "SUSPICIOUS_SHARED_PHONE"
        for issue in report.issues
    )


def test_reports_phone_not_present_in_contact_evidence() -> None:
    document = build_document(
        contacts=[
            ContactDetail(
                organization=(
                    "Nutzfahrzeug AG Zentralschweiz"
                ),
                phone="+41(0)41 666 77 00",
                address=(
                    "Hasliring 18, "
                    "CH-6032 Emmen, Switzerland"
                ),
                evidence=[
                    SourceEvidence(
                        evidence_type="forum_post",
                        post_id="498",
                        quote=(
                            "Nutzfahrzeug AG Zentralschweiz\n"
                            "Hasliring 18\n"
                            "CH-6032 Emmen\n"
                            "Tel. +41(0)41 269 00 00"
                        ),
                    )
                ],
            )
        ]
    )

    report = ContactValidator().validate(document)

    assert any(
        issue.code == "CONTACT_VALUE_NOT_IN_EVIDENCE"
        and issue.field_path == "contacts.0.phone"
        for issue in report.issues
    )


def test_reports_shared_phone_for_distinct_addresses() -> None:
    document = build_document(
        contacts=[
            ContactDetail(
                organization="Example Workshop",
                phone="+41 41 666 77 00",
                address="Address A",
                evidence=[
                    SourceEvidence(
                        evidence_type="forum_post",
                        quote=(
                            "Address A\n"
                            "+41 41 666 77 00"
                        ),
                    )
                ],
            ),
            ContactDetail(
                organization="Example Workshop",
                phone="+41 41 666 77 00",
                address="Address B",
                evidence=[
                    SourceEvidence(
                        evidence_type="forum_post",
                        quote=(
                            "Address B\n"
                            "+41 41 666 77 00"
                        ),
                    )
                ],
            ),
        ]
    )

    report = ContactValidator().validate(document)

    assert any(
        issue.code == "SUSPICIOUS_SHARED_PHONE"
        for issue in report.issues
    )