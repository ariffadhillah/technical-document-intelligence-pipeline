from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RawDatasetError(RuntimeError):
    """Raised when raw thread data cannot be loaded."""


def discover_thread_directories(
    raw_directory: Path,
) -> list[Path]:
    """
    Discover every data/raw/thread_* directory.

    Directories are sorted numerically by thread ID where possible.
    """
    if not raw_directory.exists():
        raise FileNotFoundError(
            f"Raw data directory not found: {raw_directory}"
        )

    if not raw_directory.is_dir():
        raise NotADirectoryError(
            f"Raw data path is not a directory: {raw_directory}"
        )

    thread_directories = [
        path
        for path in raw_directory.glob("thread_*")
        if path.is_dir()
    ]

    return sorted(
        thread_directories,
        key=_thread_directory_sort_key,
    )


def load_json(file_path: Path) -> dict[str, Any]:
    """Load and validate a JSON object."""
    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON file not found: {file_path}"
        )

    try:
        payload = json.loads(
            file_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        raise RawDatasetError(
            f"Invalid JSON file: {file_path}. {error}"
        ) from error

    if not isinstance(payload, dict):
        raise RawDatasetError(
            f"JSON root must be an object: {file_path}"
        )

    return payload


def load_optional_text(file_path: Path) -> str | None:
    """Read an optional UTF-8 text file."""
    if not file_path.is_file():
        return None

    return file_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def load_thread_directory(
    thread_directory: Path,
) -> dict[str, Any]:
    """
    Load one complete raw thread directory.

    thread.json is the canonical structured source.
    thread.md and thread.txt are retained as additional raw representations.
    """
    thread_json_path = thread_directory / "thread.json"
    thread_data = load_json(thread_json_path)

    metadata = thread_data.get("metadata")
    posts = thread_data.get("posts")

    if not isinstance(metadata, dict):
        raise RawDatasetError(
            f"Missing or invalid metadata: {thread_json_path}"
        )

    if not isinstance(posts, list):
        raise RawDatasetError(
            f"Missing or invalid posts: {thread_json_path}"
        )

    thread_id = metadata.get("thread_id")

    if thread_id is None:
        raise RawDatasetError(
            f"thread_id missing from: {thread_json_path}"
        )

    normalized_posts = [
        normalize_post(
            post=post,
            thread_directory=thread_directory,
        )
        for post in posts
        if isinstance(post, dict)
    ]

    return {
        "metadata": {
            **metadata,
            "raw_directory": str(
                thread_directory.resolve()
            ),
            "source_json_path": str(
                thread_json_path.resolve()
            ),
        },
        "posts": normalized_posts,
        "raw_sources": {
            "markdown": load_optional_text(
                thread_directory / "thread.md"
            ),
            "plain_text": load_optional_text(
                thread_directory / "thread.txt"
            ),
        },
    }


def normalize_post(
    post: dict[str, Any],
    thread_directory: Path,
) -> dict[str, Any]:
    """
    Normalize the downloader schema into the schema expected by
    the existing processing modules.
    """
    normalized_attachments = [
        normalize_attachment(
            attachment=attachment,
            thread_directory=thread_directory,
        )
        for attachment in post.get("attachments", [])
        if isinstance(attachment, dict)
    ]

    raw_text = post.get("text")

    if raw_text is None:
        raw_text = post.get("body", "")

    return {
        **post,
        "post_id": str(post.get("post_id", "")),
        "date": post.get("date_raw") or post.get("date"),
        "body": str(raw_text or ""),
        "text": str(raw_text or ""),
        "attachments": normalized_attachments,
    }


def normalize_attachment(
    attachment: dict[str, Any],
    thread_directory: Path,
) -> dict[str, Any]:
    """
    Preserve downloader fields while adding the legacy fields
    filename and type used by existing OCR/merger modules.
    """
    stored_name = (
        attachment.get("stored_name")
        or attachment.get("filename")
        or attachment.get("original_name")
    )

    relative_path = attachment.get("relative_path")
    local_path = resolve_attachment_path(
        thread_directory=thread_directory,
        stored_name=stored_name,
        relative_path=relative_path,
    )

    declared_kind = (
        attachment.get("kind")
        or attachment.get("type")
        or detect_attachment_kind(local_path)
    )

    return {
        **attachment,
        "filename": stored_name,
        "stored_name": stored_name,
        "type": declared_kind,
        "kind": declared_kind,
        "local_path": (
            str(local_path.resolve())
            if local_path is not None
            else None
        ),
        "file_status": (
            "available"
            if local_path is not None
            else "missing"
        ),
    }


def resolve_attachment_path(
    thread_directory: Path,
    stored_name: str | None,
    relative_path: str | None,
) -> Path | None:
    """Resolve an attachment despite differing relative-path formats."""
    candidates: list[Path] = []

    if relative_path:
        relative = Path(relative_path)

        candidates.extend(
            [
                thread_directory / relative,
                thread_directory.parent / relative,
                thread_directory.parent.parent / relative,
            ]
        )

    if stored_name:
        candidates.extend(
            thread_directory.glob(
                f"attachments/**/*{stored_name}"
            )
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def detect_attachment_kind(
    file_path: Path | None,
) -> str:
    """
    Detect PDF or image from file content.

    This also handles images saved with a .php extension.
    """
    if file_path is None:
        return "unknown"

    try:
        header = file_path.read_bytes()[:16]
    except OSError:
        return "unknown"

    if header.startswith(b"%PDF-"):
        return "pdf"

    image_signatures = (
        b"\xff\xd8\xff",
        b"\x89PNG\r\n\x1a\n",
        b"GIF87a",
        b"GIF89a",
        b"II*\x00",
        b"MM\x00*",
    )

    if any(
        header.startswith(signature)
        for signature in image_signatures
    ):
        return "image"

    if (
        header.startswith(b"RIFF")
        and header[8:12] == b"WEBP"
    ):
        return "image"

    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return "pdf"

    if suffix in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".tif",
        ".tiff",
    }:
        return "image"

    return "document"


def load_all_threads(
    raw_directory: Path,
) -> list[dict[str, Any]]:
    """Load all valid thread directories."""
    directories = discover_thread_directories(
        raw_directory
    )

    if not directories:
        raise RawDatasetError(
            f"No thread_* directories found in {raw_directory}"
        )

    return [
        load_thread_directory(directory)
        for directory in directories
    ]


def _thread_directory_sort_key(
    directory: Path,
) -> tuple[int, str]:
    value = directory.name.removeprefix("thread_")

    try:
        return int(value), directory.name
    except ValueError:
        return 10**18, directory.name