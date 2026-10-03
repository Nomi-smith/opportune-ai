from pathlib import Path

def extract_text(path: str) -> str:
    suffix = Path(path).suffix.lower()

    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix == ".docx":
        from docx import Document
        document = Document(path)
        return "\n".join(p.text for p in document.paragraphs)

    if suffix in {".txt", ".md"}:
        return Path(path).read_text(encoding="utf-8", errors="ignore")

    return ""
