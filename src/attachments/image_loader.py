from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError


def validate_image_path(image_path: Path) -> None:
    """
    Memastikan file tersedia dan benar-benar merupakan gambar.

    Validasi berdasarkan isi file menggunakan Pillow, bukan hanya
    berdasarkan ekstensi. Karena itu file forum seperti attachment.php
    tetap dapat diproses apabila isinya JPEG atau PNG.
    """
    if not image_path.exists():
        raise FileNotFoundError(
            f"File gambar tidak ditemukan: {image_path}"
        )

    if not image_path.is_file():
        raise ValueError(
            f"Path bukan file: {image_path}"
        )

    try:
        with Image.open(image_path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError(
            f"File bukan gambar valid atau rusak: {image_path.name}"
        ) from error


def load_image(image_path: Path) -> Image.Image:
    """
    Membuka gambar sebagai RGB dan membuat salinan di memori.
    """
    validate_image_path(image_path)

    with Image.open(image_path) as source_image:
        return source_image.convert("RGB").copy()


def find_images(directory: Path) -> list[Path]:
    """
    Mencari seluruh gambar secara rekursif berdasarkan isi file.

    Mendukung:
    - JPG/JPEG
    - PNG
    - WebP
    - TIFF
    - GIF
    - gambar dengan nama attachment.php
    """
    if not directory.exists():
        raise FileNotFoundError(
            f"Folder tidak ditemukan: {directory}"
        )

    if not directory.is_dir():
        raise NotADirectoryError(
            f"Path bukan folder: {directory}"
        )

    image_files: list[Path] = []

    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file():
            continue

        try:
            validate_image_path(file_path)
        except ValueError:
            continue

        image_files.append(file_path)

    return image_files