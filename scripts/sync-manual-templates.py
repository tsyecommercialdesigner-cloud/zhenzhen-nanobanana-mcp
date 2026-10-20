"""Synchronize annotated manual blocks with the delivered template files."""

import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manual = root / "MANUAL.md"
text = manual.read_text(encoding="utf-8")
pattern = r"<!-- template:([^>]+) -->\n(?:\n```.*?<!-- end-template -->\n)?"


def replace(match):
    path = root / match.group(1)
    language = "toml" if ".toml" in path.name else "yaml" if ".yml" in path.name else "json"
    content = path.read_text(encoding="utf-8").rstrip()
    return f"<!-- template:{match.group(1)} -->\n\n```{language}\n{content}\n```\n<!-- end-template -->\n"


text, count = re.subn(pattern, replace, text, flags=re.DOTALL)
assert count == 4, f"Expected four template markers, got {count}"
manual.write_text(text, encoding="utf-8")
print("Synchronized four manual templates.")
