"""
Output validation engine.

Analyzes converted Markdown files for quality issues:
  - Structural summary (heading, table, image, page counts)
  - Heading hierarchy check (skipped levels)
  - Broken internal link detection
  - Readability score (Flesch-Kincaid)
  - Missing alt-text on images

All functions are pure — they take a Markdown string and return results.
No external dependencies.
"""

import math
import os
import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Results from validating a single Markdown file."""
    # Structural counts
    heading_count: int = 0
    table_count: int = 0
    image_count: int = 0
    page_count: int = 0
    link_count: int = 0
    word_count: int = 0

    # Checks
    heading_issues: list[str] = field(default_factory=list)
    broken_links: list[str] = field(default_factory=list)
    missing_alt_texts: list[str] = field(default_factory=list)
    readability_grade: float = 0.0
    readability_label: str = ""

    @property
    def issue_count(self) -> int:
        return len(self.heading_issues) + len(self.broken_links) + len(self.missing_alt_texts)

    @property
    def passed(self) -> bool:
        return self.issue_count == 0


def validate_markdown(md: str, assets_dir: str = "") -> ValidationResult:
    """Run all validation checks on a Markdown string."""
    result = ValidationResult()

    result.heading_count = _count_headings(md)
    result.table_count = _count_tables(md)
    result.image_count = _count_images(md)
    result.page_count = _count_pages(md)
    result.link_count = _count_links(md)
    result.word_count = _count_words(md)

    result.heading_issues = _check_heading_hierarchy(md)
    result.broken_links = _check_broken_links(md, assets_dir)
    result.missing_alt_texts = _check_missing_alt_text(md)

    grade, label = _flesch_kincaid(md)
    result.readability_grade = grade
    result.readability_label = label

    return result


def validate_batch(output_root: str) -> list[ValidationResult]:
    """Validate all .md files in an output directory tree."""
    results = []
    for root, _dirs, files in os.walk(output_root):
        for fname in files:
            if fname.lower().endswith(".md"):
                path = os.path.join(root, fname)
                assets_dir = os.path.join(root, "assets")
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        md = fh.read()
                    results.append(validate_markdown(md, assets_dir))
                except Exception:
                    pass
    return results


def aggregate_validation(results: list[ValidationResult]) -> ValidationResult:
    """Merge multiple file validations into a batch summary."""
    agg = ValidationResult()
    for r in results:
        agg.heading_count += r.heading_count
        agg.table_count += r.table_count
        agg.image_count += r.image_count
        agg.page_count += r.page_count
        agg.link_count += r.link_count
        agg.word_count += r.word_count
        agg.heading_issues.extend(r.heading_issues)
        agg.broken_links.extend(r.broken_links)
        agg.missing_alt_texts.extend(r.missing_alt_texts)

    if results:
        grades = [r.readability_grade for r in results if r.readability_grade > 0]
        if grades:
            avg = sum(grades) / len(grades)
            agg.readability_grade = round(avg, 1)
            agg.readability_label = _grade_label(avg)

    return agg


# ---------------------------------------------------------------------------
# Structural counts
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r'^(#{1,6})\s+\S', re.MULTILINE)
_TABLE_SEP_RE = re.compile(r'^\|[\s:]*-+[\s:]*\|', re.MULTILINE)
_IMAGE_RE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_PAGE_ANCHOR_RE = re.compile(r'<a\s+id="page-(\d+)"', re.IGNORECASE)
_LINK_RE = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')


def _count_headings(md: str) -> int:
    return len(_HEADING_RE.findall(md))


def _count_tables(md: str) -> int:
    return len(_TABLE_SEP_RE.findall(md))


def _count_images(md: str) -> int:
    return len(_IMAGE_RE.findall(md))


def _count_pages(md: str) -> int:
    anchors = _PAGE_ANCHOR_RE.findall(md)
    return len(anchors)


def _count_links(md: str) -> int:
    return len(_LINK_RE.findall(md))


def _count_words(md: str) -> int:
    text = re.sub(r'```[\s\S]*?```', '', md)
    text = re.sub(r'---[\s\S]*?---', '', text, count=1)
    text = re.sub(r'[#*|`\[\]()>_~]', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)
    words = text.split()
    return len(words)


# ---------------------------------------------------------------------------
# Heading hierarchy check
# ---------------------------------------------------------------------------

def _check_heading_hierarchy(md: str) -> list[str]:
    """Flag skipped heading levels (e.g. H1 -> H3 with no H2)."""
    issues = []
    lines = md.split('\n')
    in_code = False
    in_front_matter = False
    prev_level = 0

    for line in lines:
        stripped = line.strip()

        if stripped == '---':
            if not in_front_matter and prev_level == 0:
                in_front_matter = True
                continue
            elif in_front_matter:
                in_front_matter = False
                continue

        if in_front_matter:
            continue

        if stripped.startswith('```'):
            in_code = not in_code
            continue

        if in_code:
            continue

        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            if prev_level > 0 and level > prev_level + 1:
                issues.append(
                    f"H{prev_level} jumps to H{level} (skipped H{prev_level + 1})"
                )
            prev_level = level

    return issues


# ---------------------------------------------------------------------------
# Broken link detection
# ---------------------------------------------------------------------------

def _check_broken_links(md: str, assets_dir: str = "") -> list[str]:
    """Check for internal links and asset references that don't resolve."""
    broken = []

    internal_anchors = set()
    for m in _PAGE_ANCHOR_RE.finditer(md):
        internal_anchors.add(f"page-{m.group(1)}")

    heading_anchors = set()
    for m in _HEADING_RE.finditer(md):
        text = md[m.end():].split('\n', 1)[0].strip() if m.end() < len(md) else ""
        if text:
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower().replace(' ', '-')
            heading_anchors.add(slug)

    all_anchors = internal_anchors | heading_anchors

    for m in _LINK_RE.finditer(md):
        link_text, url = m.group(1), m.group(2)

        if url.startswith(('#page-', '#')):
            anchor = url.lstrip('#')
            if anchor and anchor not in all_anchors:
                broken.append(f"Broken anchor: [{link_text}]({url})")

    for m in _IMAGE_RE.finditer(md):
        alt, src = m.group(1), m.group(2)
        if src.startswith('data:'):
            continue
        if src.startswith(('http://', 'https://')):
            continue
        if assets_dir:
            parent = os.path.dirname(assets_dir)
            full_path = os.path.normpath(os.path.join(parent, src))
            if not os.path.isfile(full_path):
                broken.append(f"Missing image: {src}")

    return broken


# ---------------------------------------------------------------------------
# Missing alt-text detection
# ---------------------------------------------------------------------------

def _check_missing_alt_text(md: str) -> list[str]:
    """Flag images with empty or missing alt text."""
    missing = []
    for m in _IMAGE_RE.finditer(md):
        alt_text = m.group(1).strip()
        src = m.group(2)
        if not alt_text:
            filename = os.path.basename(src) if not src.startswith('data:') else "embedded"
            missing.append(f"No alt text: {filename}")
    return missing


# ---------------------------------------------------------------------------
# Readability score (Flesch-Kincaid Grade Level)
# ---------------------------------------------------------------------------

def _flesch_kincaid(md: str) -> tuple[float, str]:
    """
    Compute Flesch-Kincaid Grade Level.
    Returns (grade_level, human_label).

    Formula:
      FK = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    """
    text = re.sub(r'```[\s\S]*?```', '', md)
    text = re.sub(r'---[\s\S]*?---', '', text, count=1)
    text = re.sub(r'[#*|`\[\]()>_~]', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    text = re.sub(r'\[[^\]]*\]\([^)]+\)', '', text)

    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = max(len(sentences), 1)

    words = []
    for s in sentences:
        words.extend(s.split())
    word_count = max(len(words), 1)

    syllable_count = sum(_count_syllables(w) for w in words)

    grade = (
        0.39 * (word_count / sentence_count)
        + 11.8 * (syllable_count / word_count)
        - 15.59
    )

    # Cap at 30 — values above that indicate the document has very few
    # sentence-ending punctuation marks relative to its word count, making
    # the formula unreliable rather than genuinely "harder to read".
    grade = max(0.0, min(30.0, round(grade, 1)))
    label = _grade_label(grade)

    return grade, label


def _count_syllables(word: str) -> int:
    """Estimate syllable count for an English word."""
    word = word.lower().strip(".,;:!?\"'()-")
    if not word:
        return 1

    if len(word) <= 3:
        return 1

    vowels = "aeiouy"
    count = 0
    prev_vowel = False

    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    if word.endswith('e') and not word.endswith('le'):
        count -= 1
    if word.endswith('ed') and len(word) > 3:
        count -= 1

    return max(count, 1)


def _grade_label(grade: float) -> str:
    """Human-readable label for a Flesch-Kincaid grade level."""
    if grade <= 5:
        return "Very Easy (Grade 5)"
    elif grade <= 8:
        return f"Easy (Grade {math.ceil(grade)})"
    elif grade <= 12:
        return f"Standard (Grade {math.ceil(grade)})"
    elif grade <= 16:
        return "College Level"
    else:
        return "Graduate Level"
