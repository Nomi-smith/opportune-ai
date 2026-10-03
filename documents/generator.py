from pathlib import Path

def write_text_document(path: str, title: str, body: str):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{title}\n\n{body}", encoding="utf-8")
    return str(output)
