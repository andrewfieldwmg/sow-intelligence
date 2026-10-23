"""Replace real names with aliases before anything is stored or sent to a model.

alias_map.csv lives outside the corpus (private/) and has columns: real,alias
e.g.  "Acme Bank plc","Client A"
Ingestion fails if any real name survives, so an unsanitised file never reaches the index.
"""
import csv
import re

from config import ALIAS_MAP_PATH

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{8,}\d)(?!\w)")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _phone(m):
    s = m.group(0)
    # Dates and short numbers look like phone numbers to the pattern; keep them.
    if DATE.search(s) or sum(ch.isdigit() for ch in s) < 10:
        return s
    return "[phone]"


class LeakError(Exception):
    pass


def load_aliases(path=ALIAS_MAP_PATH) -> list[tuple[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = [(r["real"].strip(), r["alias"].strip()) for r in csv.DictReader(f) if r["real"].strip()]
    # Longest names first so "Acme Bank plc" is replaced before "Acme".
    return sorted(rows, key=lambda r: len(r[0]), reverse=True)


def _pattern(real: str) -> str:
    # Any run of whitespace between words, so a name wrapped across a PDF line still matches.
    return r"\b" + r"\s+".join(re.escape(w) for w in real.split()) + r"\b"


def sanitise(text: str, aliases: list[tuple[str, str]]) -> str:
    text = EMAIL.sub("[email]", text)                 # before aliases, so addresses go whole
    text = PHONE.sub(_phone, text)
    for real, alias in aliases:
        text = re.sub(_pattern(real), alias, text, flags=re.IGNORECASE)
    return text


def leak_check(text: str, aliases: list[tuple[str, str]], where: str) -> None:
    for real, _ in aliases:
        if re.search(_pattern(real), text, flags=re.IGNORECASE):
            raise LeakError(f"Real name still present in {where}; fix alias_map.csv and re-run")
