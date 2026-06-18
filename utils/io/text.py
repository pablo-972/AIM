from pathlib import Path


def read_text(path: str | Path) -> str:
    target = Path(path)
    if not target.exists():
        return ""

    return target.read_text(encoding="utf-8")


def write_text(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def append_text(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("a", encoding="utf-8") as file:
        file.write(content)






