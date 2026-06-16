from pathlib import Path


def read_text(path: Path) -> str:
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as file:
        try:
            return file.read()
        except Exception as e:
            return None
    

def write_text(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def append_text(path: Path, content: str):
    with open(path, "a", encoding="utf-8") as file:
        file.write(content)






