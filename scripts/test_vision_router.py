from __future__ import annotations

from src.attachments.ocr.models import OCRPage
from src.attachments.vision import VisionRouter


def main() -> None:
    good_page = OCRPage(
        page_number=1,
        text=(
            "Installation Manual\n\n"
            "Before operating this equipment, ensure all "
            "electrical connections have been inspected."
        ),
        confidence=0.91,
        language="eng",
        metadata={
            "language_detection": {
                "language": "eng",
                "confidence": 0.95,
            }
        },
    )

    failed_page = OCRPage(
        page_number=2,
        text="@@ |1l ?? %% x",
        confidence=0.21,
        language="unknown",
        metadata={
            "language_detection": {
                "language": "unknown",
                "confidence": 0.10,
            }
        },
    )

    router = VisionRouter()

    for page in [good_page, failed_page]:
        decision = router.route(page)

        print("=" * 60)
        print("Page:", decision.page_number)
        print("OCR quality:", decision.score.quality_score)
        print("Use Vision:", decision.use_vision)
        print("Provider:", decision.provider)
        print("Priority:", decision.priority.value)
        print(
            "Reasons:",
            [
                reason.value
                for reason in decision.reasons
            ],
        )


if __name__ == "__main__":
    main()