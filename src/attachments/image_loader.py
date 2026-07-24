from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError


SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".tif",
    ".tiff",
    ".bmp",
}


def validate_image_path(
    image_path: Path,
) -> None:
    """
    Validate an image using Pillow instead of relying only
    on the filename extension.

    This supports forum images saved as attachment.php.
    """
    if not image_path.exists():
        raise FileNotFoundError(
            f"Image file not found: {image_path}"
        )

    if not image_path.is_file():
        raise ValueError(
            f"Image path is not a file: {image_path}"
        )

    try:
        with Image.open(image_path) as image:
            image.verify()
    except (
        UnidentifiedImageError,
        OSError,
    ) as error:
        raise ValueError(
            f"Unsupported or corrupted image: "
            f"{image_path.name}"
        ) from error


def load_image(
    image_path: Path,
) -> Image.Image:
    """Open an image and copy it safely into memory."""
    validate_image_path(image_path)

    with Image.open(image_path) as source_image:
        return source_image.convert("RGB").copy()


def find_images(
    directory: Path,
) -> list[Path]:
    """
    Recursively discover real images.

    Detection is based on image content, so .php attachment
    filenames are supported.
    """
    if not directory.exists():
        raise FileNotFoundError(
            f"Directory not found: {directory}"
        )

    if not directory.is_dir():
        raise NotADirectoryError(
            f"Path is not a directory: {directory}"
        )

    images: list[Path] = []

    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file():
            continue

        try:
            validate_image_path(file_path)
        except ValueError:
            continue

        images.append(file_path)

    return images