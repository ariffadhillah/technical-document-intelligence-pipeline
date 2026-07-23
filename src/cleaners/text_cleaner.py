from pathlib import Path
import json
import re


def normalize_line_endings(text: str) -> str:
    """
    Mengubah semua jenis line ending menjadi newline standar.
    """

    return text.replace("\r\n", "\n").replace("\r", "\n")


def remove_trailing_spaces(text: str) -> str:
    """
    Menghapus spasi dan tab pada akhir setiap baris.
    """

    lines = text.splitlines()

    cleaned_lines = [
        line.rstrip()
        for line in lines
    ]

    return "\n".join(cleaned_lines)


def reduce_blank_lines(text: str) -> str:
    """
    Mengurangi tiga atau lebih baris kosong menjadi satu baris kosong.
    """

    return re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )


def remove_empty_separators(text: str) -> str:
    """
    Menghapus separator Markdown yang berdiri sendiri.

    Contoh:
    --------------------
    ***
    ___
    """

    separator_pattern = re.compile(
        r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$",
        re.MULTILINE,
    )

    return separator_pattern.sub("", text)


def clean_text(text: str) -> str:
    """
    Menjalankan seluruh proses cleaning pada satu teks.
    """

    if not isinstance(text, str):
        raise TypeError("Text harus berupa string.")

    cleaned_text = normalize_line_endings(text)
    cleaned_text = remove_trailing_spaces(cleaned_text)
    cleaned_text = remove_empty_separators(cleaned_text)
    cleaned_text = reduce_blank_lines(cleaned_text)

    return cleaned_text.strip()


def clean_post(post: dict) -> dict:
    """
    Membersihkan body satu post tanpa mengubah data aslinya.
    """

    cleaned_post = post.copy()

    original_body = post.get("body", "")

    cleaned_post["body"] = clean_text(original_body)

    return cleaned_post


def clean_thread(thread_data: dict) -> dict:
    """
    Membersihkan seluruh post dalam satu thread.
    """

    cleaned_posts = [
        clean_post(post)
        for post in thread_data.get("posts", [])
    ]

    cleaned_thread_data = {
        "metadata": thread_data.get("metadata", {}).copy(),
        "posts": cleaned_posts,
    }

    cleaned_thread_data["metadata"]["processing_status"] = "cleaned"

    return cleaned_thread_data


def load_json(file_path: Path) -> dict:
    """
    Membaca file JSON.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"File JSON tidak ditemukan: {file_path}"
        )

    return json.loads(
        file_path.read_text(encoding="utf-8")
    )


def save_json(
    data: dict,
    output_path: Path,
) -> None:
    """
    Menyimpan data ke file JSON.
    """

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def print_cleaning_summary(
    original_thread: dict,
    cleaned_thread: dict,
    output_path: Path,
) -> None:
    """
    Menampilkan ringkasan proses cleaning.
    """

    original_posts = original_thread.get("posts", [])
    cleaned_posts = cleaned_thread.get("posts", [])

    original_characters = sum(
        len(post.get("body", ""))
        for post in original_posts
    )

    cleaned_characters = sum(
        len(post.get("body", ""))
        for post in cleaned_posts
    )

    print("=" * 70)
    print("THREAD TEXT CLEANER")
    print("=" * 70)

    print(
        f"Thread ID           : "
        f"{cleaned_thread['metadata'].get('thread_id')}"
    )
    print(f"Posts cleaned       : {len(cleaned_posts)}")
    print(f"Original characters : {original_characters}")
    print(f"Cleaned characters  : {cleaned_characters}")
    print(
        f"Characters removed  : "
        f"{original_characters - cleaned_characters}"
    )
    print(f"Output file         : {output_path}")
    print("Status              : success")


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    input_file = (
        project_root
        / "data"
        / "processed"
        / "thread_6260_parsed.json"
    )

    output_file = (
        project_root
        / "output"
        / "cleaned"
        / "thread_6260_cleaned.json"
    )

    thread_data = load_json(input_file)

    cleaned_thread_data = clean_thread(thread_data)

    save_json(
        cleaned_thread_data,
        output_file,
    )

    print_cleaning_summary(
        original_thread=thread_data,
        cleaned_thread=cleaned_thread_data,
        output_path=output_file,
    )


if __name__ == "__main__":
    main()