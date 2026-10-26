"""Normalización de títulos para comparar temas entre servicios."""

import re
import unicodedata

# "(feat. X)", "[with X]", "- Remastered 2011"... pero NO quita remix/edit/vip, que cambian el tema.
_FEAT_RE = re.compile(r"\s*[\(\[](feat\.?|ft\.?|with|prod\.?)\s[^\)\]]*[\)\]]", re.IGNORECASE)
_DASH_SUFFIX_RE = re.compile(r"\s+-\s+(remaster(ed)?|\d{4} remaster|radio edit|explicit|clean)\b.*$", re.IGNORECASE)


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def clean_title(title: str) -> str:
    t = _FEAT_RE.sub("", title)
    t = _DASH_SUFFIX_RE.sub("", t)
    t = strip_accents(t).lower()
    return re.sub(r"\s+", " ", t).strip()
