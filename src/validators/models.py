from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ValidationSeverity = Literal[
    "info",
    "warning",
    "error",
]


@dataclass(frozen=True)
class ValidationIssue:
    """
    One deterministic quality issue discovered in a structured document.

    The validator reports issues separately from the canonical document
    schema so existing rendering and delivery stages remain unaffected.
    """

    code: str
    message: str
    severity: ValidationSeverity = "warning"
    field_path: str | None = None
    contact_index: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "field_path": self.field_path,
            "contact_index": self.contact_index,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class ContactValidationReport:
    """
    Summary returned by ContactValidator.

    This first implementation is intentionally report-only. It does not
    mutate the structured technical document or stop the pipeline.
    """

    contact_count: int
    checked_field_count: int
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def error_count(self) -> int:
        return sum(
            issue.severity == "error"
            for issue in self.issues
        )

    @property
    def warning_count(self) -> int:
        return sum(
            issue.severity == "warning"
            for issue in self.issues
        )

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "contact_count": self.contact_count,
            "checked_field_count": self.checked_field_count,
            "issue_count": self.issue_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "passed": self.passed,
            "issues": [
                issue.to_dict()
                for issue in self.issues
            ],
        }