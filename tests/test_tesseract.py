from pathlib import Path
import pytesseract

tesseract_path = Path(
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

print("Exists :", tesseract_path.exists())

pytesseract.pytesseract.tesseract_cmd = str(
    tesseract_path
)

print(
    pytesseract.get_tesseract_version()
)

print(
    pytesseract.get_languages(config="")
)