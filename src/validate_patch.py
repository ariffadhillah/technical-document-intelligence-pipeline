from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parent

files = sorted(
    list((ROOT / "src" / "renderers").glob("*.py"))
    + list((ROOT / "src" / "rag").glob("*.py"))
)

for file_path in files:
    py_compile.compile(
        str(file_path),
        doraise=True,
    )
    print(f"[OK] {file_path.relative_to(ROOT)}")
