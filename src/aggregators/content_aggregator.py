from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


SECTION_SEPARATOR = "=" * 80
SUBSECTION_SEPARATOR = "-" * 80


@dataclass
class AggregationStatistics:
    post_count: int = 0
    attachment_count: int = 0
    image_count: int = 0
    pdf_count: int = 0
    document_count: int = 0
    forum_character_count: int = 0
    ocr_character_count: int = 0
    pdf_character_count: int = 0
    combined_character_count: int = 0
    attachment_text_count: int = 0
    empty_attachment_count: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


class ContentAggregator:
    """
    Menggabungkan forum posts dan hasil ekstraksi attachment
    menjadi satu dokumen terstruktur yang siap diproses AI.

    Supported attachment sources:
    - Image OCR
    - PDF text extraction
    - Future document extractors through `extracted_text`
    """

    def aggregate(
        self,
        thread_data: dict[str, Any],
    ) -> dict[str, Any]:
        metadata = thread_data.get("metadata", {})
        posts = thread_data.get("posts", [])

        thread_id = metadata.get("thread_id", "unknown")
        title = self._clean_text(
            metadata.get("title", "Untitled document")
        )

        statistics = AggregationStatistics(
            post_count=len(posts),
        )

        forum_sections: list[str] = []
        attachment_sections: list[str] = []

        for post_position, post in enumerate(posts, start=1):
            forum_section = self._build_post_section(
                post=post,
                position=post_position,
            )

            if forum_section:
                forum_sections.append(forum_section)
                statistics.forum_character_count += len(
                    self._get_post_body(post)
                )

            for attachment_position, attachment in enumerate(
                post.get("attachments", []),
                start=1,
            ):
                statistics.attachment_count += 1

                attachment_type = self._get_attachment_type(
                    attachment
                )

                self._increment_attachment_type(
                    statistics=statistics,
                    attachment_type=attachment_type,
                )

                extracted_text = self._get_attachment_text(
                    attachment
                )

                if not extracted_text:
                    statistics.empty_attachment_count += 1
                    continue

                statistics.attachment_text_count += 1

                character_count = len(extracted_text)

                if attachment_type == "image":
                    statistics.ocr_character_count += (
                        character_count
                    )
                elif attachment_type == "pdf":
                    statistics.pdf_character_count += (
                        character_count
                    )

                attachment_sections.append(
                    self._build_attachment_section(
                        attachment=attachment,
                        extracted_text=extracted_text,
                        post=post,
                        position=attachment_position,
                    )
                )

        forum_text = "\n\n".join(forum_sections).strip()
        attachment_text = "\n\n".join(
            attachment_sections
        ).strip()

        combined_text = self._build_combined_document(
            thread_id=thread_id,
            title=title,
            metadata=metadata,
            forum_text=forum_text,
            attachment_text=attachment_text,
        )

        statistics.combined_character_count = len(
            combined_text
        )

        return {
            "document_id": f"thread_{thread_id}",
            "document_type": "forum_thread",
            "title": title,
            "source_language": metadata.get(
                "source_language",
                "unknown",
            ),
            "source": {
                "thread_id": thread_id,
                "source_url": metadata.get("source_url"),
                "forum_name": metadata.get("forum_name"),
                "forum_url": metadata.get("forum_url"),
            },
            "content": {
                "forum_text": forum_text,
                "attachment_text": attachment_text,
                "combined_text": combined_text,
            },
            "statistics": statistics.to_dict(),
            "processing": {
                "input_stage": metadata.get(
                    "processing_status",
                    "unknown",
                ),
                "output_stage": "content_aggregated",
                "ready_for_ai": bool(combined_text.strip()),
            },
        }

    def _build_combined_document(
        self,
        thread_id: int | str,
        title: str,
        metadata: dict[str, Any],
        forum_text: str,
        attachment_text: str,
    ) -> str:
        sections: list[str] = [
            SECTION_SEPARATOR,
            "TECHNICAL DOCUMENT",
            SECTION_SEPARATOR,
            f"Document ID: thread_{thread_id}",
            f"Document Type: forum_thread",
            f"Title: {title}",
            (
                "Source Language: "
                f"{metadata.get('source_language', 'unknown')}"
            ),
            (
                "Source URL: "
                f"{metadata.get('source_url', '')}"
            ),
        ]

        if metadata.get("forum_name"):
            sections.append(
                f"Forum: {metadata['forum_name']}"
            )

        sections.extend(
            [
                "",
                SECTION_SEPARATOR,
                "FORUM DISCUSSION",
                SECTION_SEPARATOR,
                forum_text or "[No forum text available]",
            ]
        )

        sections.extend(
            [
                "",
                SECTION_SEPARATOR,
                "EXTRACTED ATTACHMENT CONTENT",
                SECTION_SEPARATOR,
                (
                    attachment_text
                    or "[No extracted attachment text available]"
                ),
            ]
        )

        sections.extend(
            [
                "",
                SECTION_SEPARATOR,
                "END OF DOCUMENT",
                SECTION_SEPARATOR,
            ]
        )

        return "\n".join(sections).strip()

    def _build_post_section(
        self,
        post: dict[str, Any],
        position: int,
    ) -> str:
        body = self._get_post_body(post)

        if not body:
            return ""

        post_id = post.get("post_id", "unknown")
        author = self._clean_text(
            post.get("author", "unknown")
        )
        date = (
            post.get("date")
            or post.get("date_raw")
            or "unknown"
        )
        source_page_url = post.get(
            "source_page_url",
            "",
        )

        lines = [
            SUBSECTION_SEPARATOR,
            f"POST #{position}",
            SUBSECTION_SEPARATOR,
            f"Post ID: {post_id}",
            f"Author: {author}",
            f"Date: {date}",
        ]

        if source_page_url:
            lines.append(
                f"Source Page: {source_page_url}"
            )

        lines.extend(
            [
                "",
                "Body:",
                body,
            ]
        )

        return "\n".join(lines).strip()

    def _build_attachment_section(
        self,
        attachment: dict[str, Any],
        extracted_text: str,
        post: dict[str, Any],
        position: int,
    ) -> str:
        attachment_type = self._get_attachment_type(
            attachment
        )

        filename = (
            attachment.get("original_name")
            or attachment.get("filename")
            or attachment.get("stored_name")
            or "unknown"
        )

        method = attachment.get(
            "extraction_method",
            "unknown",
        )

        status = attachment.get(
            "processing_status",
            "unknown",
        )

        lines = [
            SUBSECTION_SEPARATOR,
            (
                f"{attachment_type.upper()} "
                f"ATTACHMENT #{position}"
            ),
            SUBSECTION_SEPARATOR,
            f"Post ID: {post.get('post_id', 'unknown')}",
            f"Filename: {filename}",
            f"Type: {attachment_type}",
            f"Extraction Method: {method}",
            f"Processing Status: {status}",
        ]

        source_url = attachment.get("source_url")

        if source_url:
            lines.append(f"Source URL: {source_url}")

        ocr_data = attachment.get("ocr", {})

        if attachment_type == "image" and ocr_data:
            confidence = ocr_data.get("confidence")
            language = ocr_data.get("language")

            if language:
                lines.append(
                    f"OCR Language: {language}"
                )

            if confidence is not None:
                lines.append(
                    f"OCR Confidence: {confidence}"
                )

        pdf_data = attachment.get(
            "pdf_extraction",
            {},
        )

        if attachment_type == "pdf" and pdf_data:
            lines.append(
                "PDF Classification: "
                f"{pdf_data.get('classification', 'unknown')}"
            )
            lines.append(
                "Page Count: "
                f"{pdf_data.get('page_count', 0)}"
            )
            lines.append(
                "Requires OCR: "
                f"{pdf_data.get('requires_ocr', False)}"
            )

        lines.extend(
            [
                "",
                "Extracted Text:",
                extracted_text,
            ]
        )

        return "\n".join(lines).strip()

    @staticmethod
    def _get_post_body(
        post: dict[str, Any],
    ) -> str:
        value = (
            post.get("body")
            or post.get("cleaned_text")
            or post.get("text")
            or ""
        )

        return ContentAggregator._clean_text(value)

    @staticmethod
    def _get_attachment_text(
        attachment: dict[str, Any],
    ) -> str:
        value = attachment.get("extracted_text")

        if not value:
            ocr_data = attachment.get("ocr", {})
            value = ocr_data.get("raw_text")

        if not value:
            pdf_data = attachment.get(
                "pdf_extraction",
                {},
            )
            value = pdf_data.get("raw_text")

        return ContentAggregator._clean_text(value)

    @staticmethod
    def _get_attachment_type(
        attachment: dict[str, Any],
    ) -> str:
        value = (
            attachment.get("kind")
            or attachment.get("type")
            or "document"
        )

        return str(value).strip().lower()

    @staticmethod
    def _increment_attachment_type(
        statistics: AggregationStatistics,
        attachment_type: str,
    ) -> None:
        if attachment_type == "image":
            statistics.image_count += 1
        elif attachment_type == "pdf":
            statistics.pdf_count += 1
        else:
            statistics.document_count += 1

    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None:
            return ""

        text = str(value)

        normalized_lines = [
            line.rstrip()
            for line in text.replace(
                "\r\n",
                "\n",
            ).replace(
                "\r",
                "\n",
            ).split("\n")
        ]

        result_lines: list[str] = []
        previous_blank = False

        for line in normalized_lines:
            is_blank = not line.strip()

            if is_blank and previous_blank:
                continue

            result_lines.append(line)
            previous_blank = is_blank

        return "\n".join(result_lines).strip()