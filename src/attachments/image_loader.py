from pathlib import Path

from PIL import Image


SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
}


def validate_image_path(image_path: Path) -> None:
    """
    Memastikan file gambar tersedia dan formatnya didukung.
    """

    if not image_path.exists():
        raise FileNotFoundError(
            f"File gambar tidak ditemukan: {image_path}"
        )

    if not image_path.is_file():
        raise ValueError(
            f"Path bukan file: {image_path}"
        )

    if image_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Format gambar tidak didukung: {image_path.name}"
        )


def load_image(image_path: Path) -> Image.Image:
    """
    Membuka gambar dan membuat salinan ke memori.

    Salinan dibuat agar file asli dapat langsung ditutup.
    """

    validate_image_path(image_path)

    with Image.open(image_path) as source_image:
        return source_image.copy()


def find_images(directory: Path) -> list[Path]:
    """
    Mencari seluruh file gambar dalam sebuah folder.
    """

    if not directory.exists():
        raise FileNotFoundError(
            f"Folder tidak ditemukan: {directory}"
        )

    if not directory.is_dir():
        raise NotADirectoryError(
            f"Path bukan folder: {directory}"
        )

    return sorted(
        file_path
        for file_path in directory.iterdir()
        if (
            file_path.is_file()
            and file_path.suffix.lower()
            in SUPPORTED_IMAGE_EXTENSIONS
        )
    )