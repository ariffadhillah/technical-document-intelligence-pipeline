from pathlib import Path
import re


ATTACHMENT_PATTERN = re.compile(
    r"^- \[Referenced image: (?P<filename>.+?)\]$",
    re.MULTILINE,
)


def extract_attachments(post_body: str) -> list[dict]:
    """
    Mengambil referensi attachment dari body post.
    """

    attachments = []

    for match in ATTACHMENT_PATTERN.finditer(post_body):
        filename = match.group("filename").strip()

        file_extension = Path(filename).suffix.lower()

        if file_extension in [".jpg", ".jpeg", ".png", ".webp"]:
            attachment_type = "image"

        elif file_extension == ".pdf":
            attachment_type = "pdf"

        else:
            attachment_type = "unknown"

        attachments.append(
            {
                "filename": filename,
                "type": attachment_type,
            }
        )

    return attachments


def remove_attachment_section(post_body: str) -> str:
    """
    Menghapus blok attachment dari body post.

    Attachment tetap disimpan secara terpisah.
    """

    cleaned_body = re.sub(
        r"\n*\*\*Attachments:\*\*\n"
        r"(?:- \[Referenced image: .+?\]\n?)+",
        "",
        post_body,
        flags=re.MULTILINE,
    )

    return cleaned_body.strip()


def read_markdown_file(file_path: Path) -> str:
    """
    Membaca isi file Markdown.
    """

    if not file_path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {file_path}")

    return file_path.read_text(encoding="utf-8")


def parse_front_matter(markdown_text: str) -> dict:
    """
    Membaca metadata YAML sederhana di bagian atas file Markdown.

    Contoh:

    ---
    thread_id: 6260
    thread_title: "Kat 1A1.1 6x6"
    source_language: "de"
    ---
    """

    pattern = r"\A---\s*\n(.*?)\n---"
    match = re.search(pattern, markdown_text, re.DOTALL)

    if not match:
        raise ValueError("YAML front matter tidak ditemukan.")

    front_matter_text = match.group(1)

    metadata = {}

    for line in front_matter_text.splitlines():
        line = line.strip()

        if not line:
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip()
        value = value.strip()

        # Menghapus tanda kutip
        value = value.strip('"').strip("'")

        # Mengubah angka menjadi integer
        if value.isdigit():
            value = int(value)

        # Mengubah boolean
        elif value.lower() == "true":
            value = True

        elif value.lower() == "false":
            value = False

        metadata[key] = value

    return metadata


def parse_posts(markdown_text: str) -> list[dict]:
    """
    Mengambil semua post dari file Markdown.
    """

    post_pattern = re.compile(
        r"## Post (?P<post_id>[^\n]+)\n+"
        r"\*\*Author:\*\* (?P<author>.*?)\s{2,}\n"
        r"\*\*Date:\*\* (?P<date>.*?)\s{2,}\n+"
        r"(?P<body>.*?)(?=\n---|\Z)",
        re.DOTALL,
    )

    posts = []

    for match in post_pattern.finditer(markdown_text):
        raw_body = match.group("body").strip()

        attachments = extract_attachments(raw_body)
        clean_body = remove_attachment_section(raw_body)

        post = {
            "post_id": match.group("post_id").strip(),
            "author": match.group("author").strip(),
            "date": match.group("date").strip(),
            "body": clean_body,
            "attachments": attachments,
        }

        posts.append(post)

    return posts


def parse_thread(file_path: Path) -> dict:
    """
    Fungsi utama untuk membaca satu thread.
    """

    markdown_text = read_markdown_file(file_path)

    metadata = parse_front_matter(markdown_text)
    posts = parse_posts(markdown_text)

    thread_data = {
        "metadata": metadata,
        "posts": posts,
    }

    return thread_data


def print_thread_summary(thread_data: dict) -> None:
    """
    Menampilkan ringkasan hasil parsing ke terminal.
    """

    metadata = thread_data["metadata"]
    posts = thread_data["posts"]

    print("=" * 70)
    print("RAW THREAD PARSER")
    print("=" * 70)

    print(f"Thread ID       : {metadata.get('thread_id')}")
    print(f"Thread title    : {metadata.get('thread_title')}")
    print(f"Forum section   : {metadata.get('forum_section')}")
    print(f"Source URL      : {metadata.get('source_url')}")
    print(f"Source language : {metadata.get('source_language')}")
    print(f"Expected posts  : {metadata.get('post_count')}")
    print(f"Parsed posts    : {len(posts)}")

    print("\nPost IDs:")


    for post in posts:
        attachment_count = len(post["attachments"])

        print(
            f"- {post['post_id']} | "
            f"{post['author']} | "
            f"{post['date']} | "
            f"attachments: {attachment_count}"
        )


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]

    thread_file = (
        project_root
        / "data"
        / "raw"
        / "text_logs"
        / "thread_6260.md"
    )

    thread_data = parse_thread(thread_file)

    print_thread_summary(thread_data)


if __name__ == "__main__":
    main()