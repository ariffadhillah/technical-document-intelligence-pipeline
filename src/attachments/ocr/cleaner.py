from __future__ import annotations

import re
import unicodedata

from .models import OCRDocument, OCRPage


class OCRTextCleaner:
    """
    Clean common OCR artifacts while preserving
    useful document structure.
    """

    def clean_text(
        self,
        text: str,
    ) -> str:

        if not text:
            return ""

        text = self.normalize_unicode(text)

        text = self.remove_control_characters(text)

        text = self.fix_hyphenated_line_breaks(text)

        text = self.normalize_spaces(text)

        text = self.normalize_line_breaks(text)

        text = self.remove_empty_page_noise(text)

        return text.strip()

    def clean_page(
        self,
        page: OCRPage,
    ) -> OCRPage:

        page.text = self.clean_text(page.text)

        for paragraph in page.paragraphs:
            paragraph.text = self.clean_text(
                paragraph.text
            )

            for line in paragraph.lines:
                line.text = self.clean_text(
                    line.text
                )

                for word in line.words:
                    word.text = self.clean_word(
                        word.text
                    )

        return page

    def clean_document(
        self,
        document: OCRDocument,
    ) -> OCRDocument:

        document.pages = [
            self.clean_page(page)
            for page in document.pages
        ]

        document.text = self.clean_text(
            "\n\n".join(
                page.text
                for page in document.pages
                if page.text.strip()
            )
        )

        return document

    @staticmethod
    def normalize_unicode(
        text: str,
    ) -> str:

        return unicodedata.normalize(
            "NFKC",
            text,
        )

    @staticmethod
    def remove_control_characters(
        text: str,
    ) -> str:

        return "".join(
            character
            for character in text
            if (
                character in "\n\t"
                or not unicodedata.category(
                    character
                ).startswith("C")
            )
        )

    @staticmethod
    def fix_hyphenated_line_breaks(
        text: str,
    ) -> str:
        """
        Convert:

            hydrau-
            lic

        into:

            hydraulic
        """

        return re.sub(
            r"(?<=\w)-\s*\n\s*(?=\w)",
            "",
            text,
        )

    @staticmethod
    def normalize_spaces(
        text: str,
    ) -> str:

        text = re.sub(
            r"[ \t]+",
            " ",
            text,
        )

        text = re.sub(
            r" +\n",
            "\n",
            text,
        )

        return text

    @staticmethod
    def normalize_line_breaks(
        text: str,
    ) -> str:

        text = text.replace("\r\n", "\n")

        text = text.replace("\r", "\n")

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text

    @staticmethod
    def remove_empty_page_noise(
        text: str,
    ) -> str:

        lines = []

        for line in text.splitlines():
            cleaned = line.strip()

            if not cleaned:
                lines.append("")
                continue

            if re.fullmatch(
                r"[_\-=*~.]{4,}",
                cleaned,
            ):
                continue

            lines.append(cleaned)

        return "\n".join(lines)

    @staticmethod
    def clean_word(
        word: str,
    ) -> str:

        word = unicodedata.normalize(
            "NFKC",
            word,
        )

        return word.strip()