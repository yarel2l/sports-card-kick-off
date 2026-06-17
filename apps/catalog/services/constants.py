"""
Domain vocabulary for parsing and normalizing sports card listings.

These tables are intentionally data-driven so the title parser and the
resolver stay rule-based and testable. They can later be backed by the
database (e.g. a managed ``CardSet`` checklist) without changing callers.
"""

# ---------------------------------------------------------------------------
# Sports
# ---------------------------------------------------------------------------
SPORT_BASKETBALL = 'BASKETBALL'
SPORT_FOOTBALL = 'FOOTBALL'
SPORT_BASEBALL = 'BASEBALL'
SPORT_HOCKEY = 'HOCKEY'
SPORT_SOCCER = 'SOCCER'
SPORT_OTHER = 'OTHER'

SPORT_CHOICES = (
    (SPORT_BASKETBALL, 'Basketball'),
    (SPORT_FOOTBALL, 'Football'),
    (SPORT_BASEBALL, 'Baseball'),
    (SPORT_HOCKEY, 'Hockey'),
    (SPORT_SOCCER, 'Soccer'),
    (SPORT_OTHER, 'Other'),
)

# ---------------------------------------------------------------------------
# Brands (manufacturers). Multi-word brands MUST come before single-word ones
# so the longest match wins during scanning.
# ---------------------------------------------------------------------------
BRANDS = (
    'Upper Deck',
    'Panini',
    'Topps',
    'Bowman',
    'Fleer',
    'Donruss',
    'Score',
    'Leaf',
    'Sage',
    'Press Pass',
    'Pro Set',
    'O-Pee-Chee',
)

# ---------------------------------------------------------------------------
# Product lines / sets. Multi-word lines first. Each maps to the brand that
# publishes it, so a brand can be inferred when the title only names the set
# (e.g. "Prizm" -> Panini, "Chrome" -> Topps).
# ---------------------------------------------------------------------------
SET_TO_BRAND = {
    'Bowman Chrome': 'Bowman',
    'Bowman Draft': 'Bowman',
    'Bowman Sterling': 'Bowman',
    'Topps Chrome': 'Topps',
    'Stadium Club': 'Topps',
    'Allen & Ginter': 'Topps',
    'Gallery': 'Topps',
    'Heritage': 'Topps',
    'Finest': 'Topps',
    'Fire': 'Topps',
    'Prizm': 'Panini',
    'Optic': 'Panini',
    'Donruss Optic': 'Panini',
    'Select': 'Panini',
    'Mosaic': 'Panini',
    'Spectra': 'Panini',
    'Obsidian': 'Panini',
    'Contenders': 'Panini',
    'National Treasures': 'Panini',
    'Flawless': 'Panini',
    'Immaculate': 'Panini',
    'Hoops': 'Panini',
    'Chronicles': 'Panini',
    'Revolution': 'Panini',
    'Crown Royale': 'Panini',
    'Chrome': 'Topps',
    'Sapphire': 'Topps',
}

# Ordered longest-first for greedy matching.
PRODUCT_LINES = tuple(
    sorted(SET_TO_BRAND.keys(), key=lambda s: len(s), reverse=True)
)

# ---------------------------------------------------------------------------
# Parallels / variations. Longest-first for greedy matching.
# ---------------------------------------------------------------------------
PARALLELS = (
    'Cracked Ice',
    'Fast Break',
    'Color Blast',
    'Gold Vinyl',
    'White Sparkle',
    'Shock',
    'Hyper',
    'Disco',
    'Mojo',
    'Wave',
    'Scope',
    'Pulsar',
    'Negative',
    'Holo',
    'Holographic',
    'Shimmer',
    'Refractor',
    'Prizm',
    'Silver',
    'Gold',
    'Black',
    'Red',
    'Blue',
    'Green',
    'Orange',
    'Purple',
    'Pink',
    'Bronze',
    'Teal',
)
PARALLELS = tuple(sorted(PARALLELS, key=lambda s: len(s), reverse=True))

# ---------------------------------------------------------------------------
# Grading companies. Normalizes common aliases to a canonical code.
# ---------------------------------------------------------------------------
GRADING_COMPANY_ALIASES = {
    'PSA': 'PSA',
    'BGS': 'BGS',
    'BECKETT': 'BGS',
    'BVG': 'BGS',
    'SGC': 'SGC',
    'CGC': 'CGC',
    'CSG': 'CSG',
    'HGA': 'HGA',
    'TAG': 'TAG',
}

GRADING_COMPANY_NAMES = {
    'PSA': 'Professional Sports Authenticator',
    'BGS': 'Beckett Grading Services',
    'SGC': 'Sportscard Guaranty Company',
    'CGC': 'Certified Guaranty Company',
    'CSG': 'Certified Sports Guaranty',
    'HGA': 'Hybrid Grading Approach',
    'TAG': 'Technical Authentication & Grading',
    'RAW': 'Raw / Ungraded',
}

# Ordered longest-first so "BECKETT" matches before any single token.
GRADING_COMPANY_TOKENS = tuple(
    sorted(GRADING_COMPANY_ALIASES.keys(), key=lambda s: len(s), reverse=True)
)

# Tokens that are never part of a player name.
ATTRIBUTE_STOPWORDS = {
    'rookie', 'rc', 'auto', 'autograph', 'autographed', 'signed', 'signature',
    'patch', 'jersey', 'relic', 'memorabilia', 'rpa', 'ssp', 'sp', 'case',
    'hit', 'insert', 'parallel', 'card', 'mint', 'gem', 'graded', 'lot',
    'of', 'the', 'and', 'rookies', 'on', 'rated', 'prizm', 'refractor',
    'variation', 'short', 'print', 'die', 'cut',
}
