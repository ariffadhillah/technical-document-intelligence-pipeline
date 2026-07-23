from PIL import Image, ImageEnhance, ImageFilter, ImageOps


MINIMUM_OCR_WIDTH = 1600


def resize_for_ocr(
    image: Image.Image,
    minimum_width: int = MINIMUM_OCR_WIDTH,
) -> Image.Image:
    """
    Memperbesar gambar kecil agar teks lebih mudah dibaca OCR.
    """

    width, height = image.size

    if width >= minimum_width:
        return image

    scale_factor = minimum_width / width

    resized_dimensions = (
        int(width * scale_factor),
        int(height * scale_factor),
    )

    return image.resize(
        resized_dimensions,
        Image.Resampling.LANCZOS,
    )


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Menyiapkan gambar untuk OCR.

    Tahapan:
    - memperbaiki orientasi EXIF;
    - mengubah gambar ke grayscale;
    - memperbesar gambar kecil;
    - meningkatkan kontras;
    - mempertajam teks.
    """

    processed_image = ImageOps.exif_transpose(image)
    processed_image = processed_image.convert("L")

    processed_image = resize_for_ocr(
        processed_image
    )

    processed_image = ImageOps.autocontrast(
        processed_image
    )

    processed_image = ImageEnhance.Contrast(
        processed_image
    ).enhance(1.5)

    processed_image = processed_image.filter(
        ImageFilter.SHARPEN
    )

    return processed_image