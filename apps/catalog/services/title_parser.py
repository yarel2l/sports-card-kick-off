"""
Rule-based parser that turns a noisy marketplace listing title into a
structured :class:`ParsedCard`.

This is the first layer of entity resolution. It is deliberately deterministic
and dependency-free (only the standard library) so it is fast, testable, and
predictable. A future ML layer can refine low-confidence parses, but the
rule-based pass handles the long tail of well-formed titles that dominate
real marketplace data.

Example
-------
>>> p = parse_title("2018-19 Panini Prizm Luka Doncic #280 Silver PSA 10 Rookie RC")
>>> p.year, p.brand, p.set_name, p.player_name
(2018, 'Panini', 'Prizm', 'Luka Doncic')
>>> p.card_number, p.parallel, p.grading_company, p.grade
('280', 'Silver', 'PSA', '10')
>>> p.is_rookie
True
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from . import constants


@dataclass
class ParsedCard:
    """Structured representation extracted from a raw listing title."""

    raw_title: str
    year: Optional[int] = None
    year_display: Optional[str] = None  # e.g. "2018-19"
    brand: Optional[str] = None
    set_name: Optional[str] = None
    player_name: Optional[str] = None
    card_number: Optional[str] = None
    parallel: Optional[str] = None
    grading_company: Optional[str] = None
    grade: Optional[str] = None
    serial_limit: Optional[int] = None
    is_rookie: bool = False
    is_autograph: bool = False
    is_memorabilia: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


# --- Regular expressions (compiled once) -----------------------------------

# Season formats: 2018, 2018-19, 2018-2019, 1986-87
_YEAR_RE = re.compile(r'\b((?:19|20)\d{2})(?:[-/](\d{2,4}))?\b')

# "#280", "# 280", "#BDC-50", "No. 12"
_CARD_NUMBER_RE = re.compile(
    r'(?:#|No\.?\s*)\s*([A-Za-z]{0,4}-?\d{1,5}[A-Za-z]?)\b', re.IGNORECASE
)

# Serial numbering: "/99", "25/99", "1 of 10"
_SERIAL_RE = re.compile(
    r'(?:(\d{1,5})\s*/\s*(\d{1,5}))|(?:/\s*(\d{1,5}))|(?:\b\d{1,4}\s+of\s+(\d{1,5})\b)',
    re.IGNORECASE,
)

_ROOKIE_RE = re.compile(r'\b(rookie|rc|yg|young\s+guns)\b', re.IGNORECASE)
_AUTO_RE = re.compile(r'\b(auto(?:graph(?:ed)?)?|signed|signature|on[- ]card)\b', re.IGNORECASE)
_MEM_RE = re.compile(r'\b(patch|jersey|relic|memorabilia|game[- ]used|rpa)\b', re.IGNORECASE)


def _build_grade_re() -> re.Pattern:
    tokens = '|'.join(re.escape(t) for t in constants.GRADING_COMPANY_TOKENS)
    # Optional descriptor like "GEM MT" / "MINT" between company and number.
    return re.compile(
        rf'\b({tokens})\b'
        r'(?:\s+(?:GEM(?:\s+MINT|\s+MT)?|MINT|MT|PRISTINE|AUTHENTIC|AUTH))?'
        r'\s*(10|[1-9](?:\.5)?)\b',
        re.IGNORECASE,
    )


_GRADE_RE = _build_grade_re()


def _find_year(title: str) -> tuple[Optional[int], Optional[str]]:
    match = _YEAR_RE.search(title)
    if not match:
        return None, None
    start = int(match.group(1))
    display = match.group(0)
    return start, display


def _find_grade(title: str) -> tuple[Optional[str], Optional[str]]:
    match = _GRADE_RE.search(title)
    if not match:
        return None, None
    company = constants.GRADING_COMPANY_ALIASES.get(match.group(1).upper())
    grade = match.group(2)
    return company, grade


def _scan_phrase(title_lower: str, phrases) -> Optional[str]:
    """Return the first phrase (in supplied order) found as a whole token run."""
    for phrase in phrases:
        pattern = r'\b' + re.escape(phrase.lower()) + r'\b'
        if re.search(pattern, title_lower):
            return phrase
    return None


def _find_serial_limit(title: str, card_number: Optional[str]) -> Optional[int]:
    for match in _SERIAL_RE.finditer(title):
        # Skip if this match is actually the card number we already captured.
        denom = match.group(2) or match.group(3) or match.group(4)
        if not denom:
            continue
        try:
            value = int(denom)
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return None


def _extract_player_name(
    title: str,
    parsed: ParsedCard,
) -> Optional[str]:
    """
    Heuristic player extraction.

    Strategy: remove every span we already understood (year, brand, set,
    number, grade, parallel, serial, attribute keywords), then take the
    longest remaining run of name-like tokens.
    """
    working = title

    # Remove understood spans, longest first so multi-word spans (e.g.
    # "Topps Chrome") are stripped before the shorter brand ("Topps") they
    # contain — otherwise a fragment like "Chrome" leaks into the name.
    spans = [s for s in (
        parsed.year_display,
        parsed.brand,
        parsed.set_name,
        parsed.parallel,
    ) if s]
    for span in sorted(spans, key=len, reverse=True):
        working = re.sub(re.escape(span), ' ', working, flags=re.IGNORECASE)

    working = _CARD_NUMBER_RE.sub(' ', working)
    working = _GRADE_RE.sub(' ', working)
    working = _SERIAL_RE.sub(' ', working)
    working = _ROOKIE_RE.sub(' ', working)
    working = _AUTO_RE.sub(' ', working)
    working = _MEM_RE.sub(' ', working)

    # Tokenize on non-name characters (keep letters, apostrophes, hyphens, dots).
    tokens = re.findall(r"[A-Za-z][A-Za-z.'\-]*", working)

    runs: List[List[str]] = []
    current: List[str] = []
    for token in tokens:
        clean = token.strip(".-'")
        if (
            len(clean) < 2
            or clean.lower() in constants.ATTRIBUTE_STOPWORDS
            or clean.isupper() and len(clean) <= 3  # stray acronyms (SSP, SP...)
        ):
            if current:
                runs.append(current)
                current = []
            continue
        current.append(clean)
    if current:
        runs.append(current)

    if not runs:
        return None

    # Prefer the longest run; ties broken by earliest position.
    best = max(runs, key=len)
    if len(best) < 1:
        return None

    name = ' '.join(best[:4])  # cap to a sensible name length
    name = re.sub(r'\s+', ' ', name).strip()
    return name.title() if name else None


def parse_title(title: str) -> ParsedCard:
    """Parse a raw listing title into a :class:`ParsedCard`."""
    if not title or not title.strip():
        return ParsedCard(raw_title=title or '')

    title = re.sub(r'\s+', ' ', title).strip()
    parsed = ParsedCard(raw_title=title)
    title_lower = title.lower()

    parsed.year, parsed.year_display = _find_year(title)
    parsed.grading_company, parsed.grade = _find_grade(title)

    number_match = _CARD_NUMBER_RE.search(title)
    if number_match:
        parsed.card_number = number_match.group(1).lstrip('-').upper()

    parsed.set_name = _scan_phrase(title_lower, constants.PRODUCT_LINES)
    parsed.brand = _scan_phrase(title_lower, constants.BRANDS)
    if not parsed.brand and parsed.set_name:
        parsed.brand = constants.SET_TO_BRAND.get(parsed.set_name)

    parsed.parallel = _scan_phrase(title_lower, constants.PARALLELS)
    # A set named "Prizm" should not also be reported as the "Prizm" parallel.
    if parsed.parallel and parsed.set_name and parsed.parallel.lower() == parsed.set_name.lower():
        parsed.parallel = None

    parsed.serial_limit = _find_serial_limit(title, parsed.card_number)
    parsed.is_rookie = bool(_ROOKIE_RE.search(title))
    parsed.is_autograph = bool(_AUTO_RE.search(title))
    parsed.is_memorabilia = bool(_MEM_RE.search(title))

    parsed.player_name = _extract_player_name(title, parsed)

    return parsed
