"""
Post-processing functions for converted document text.

These run between raw extraction and final output assembly. Each function
is opt-in, controlled by a settings toggle. The pipeline order matters:

    1. remove_headers_footers  — strip repeated page headers/footers
    2. filter_blank_pages      — drop empty pages
    3. strip_line_numbers      — remove margin line numbers
    4. (Milestone B) detect_code_blocks
    5. (Milestone B) detect_footnotes
    6. (Milestone C) detect_equations

All functions are pure: they take text in and return text out with no
side effects. Logging is handled by the caller.
"""

import re
from collections import Counter


# ---------------------------------------------------------------------------
# 1. Header / Footer Removal
# ---------------------------------------------------------------------------

def remove_headers_footers(
    pages: list[str],
    top_lines: int = 3,
    bottom_lines: int = 3,
    min_pages: int = 3,
) -> list[str]:
    """
    Remove repeated text that appears at the top or bottom of most pages.

    Algorithm:
      - For each page, extract the first *top_lines* and last *bottom_lines*
        lines of text.
      - Normalize each line (strip whitespace, collapse runs of spaces).
      - Count how often each normalized line appears across all pages.
      - A line is classified as a header/footer if it appears on at least
        *min_pages* pages **and** on at least 50 % of all pages.
      - Matching lines are stripped from every page.

    Returns a new list of cleaned page strings (same length as input).
    """
    if len(pages) < min_pages:
        return list(pages)

    threshold = max(min_pages, len(pages) // 2)

    # Collect candidate header/footer lines per page
    top_counter: Counter[str] = Counter()
    bottom_counter: Counter[str] = Counter()

    for page_text in pages:
        lines = page_text.splitlines()
        # Use a set per page so a line on the same page counts only once
        top_set = set()
        bottom_set = set()

        for line in lines[:top_lines]:
            norm = _normalize(line)
            if norm:
                top_set.add(norm)
        for line in lines[-bottom_lines:] if len(lines) > bottom_lines else lines[-1:]:
            norm = _normalize(line)
            if norm:
                bottom_set.add(norm)

        for n in top_set:
            top_counter[n] += 1
        for n in bottom_set:
            bottom_counter[n] += 1

    # Build sets of lines to remove
    header_lines = {line for line, count in top_counter.items() if count >= threshold}
    footer_lines = {line for line, count in bottom_counter.items() if count >= threshold}
    removable = header_lines | footer_lines

    if not removable:
        return list(pages)

    # Strip matching lines from every page
    cleaned = []
    for page_text in pages:
        out_lines = []
        for line in page_text.splitlines():
            if _normalize(line) not in removable:
                out_lines.append(line)
        cleaned.append("\n".join(out_lines))

    return cleaned


def _normalize(line: str) -> str:
    """Collapse whitespace and strip for comparison."""
    return re.sub(r"\s+", " ", line.strip())


# ---------------------------------------------------------------------------
# 2. Blank Page Skipping
# ---------------------------------------------------------------------------

def is_blank_page(text: str, threshold: int = 10) -> bool:
    """
    Return True if *text* contains fewer than *threshold* non-whitespace
    characters. A threshold of 10 catches pages with just a page number
    or a stray header/footer remnant.
    """
    non_ws = sum(1 for ch in text if not ch.isspace())
    return non_ws < threshold


def filter_blank_pages(
    pages: list[str],
    threshold: int = 10,
) -> list[str]:
    """Return only pages that are not effectively blank."""
    return [p for p in pages if not is_blank_page(p, threshold)]


# ---------------------------------------------------------------------------
# 3. Line Number Stripping
# ---------------------------------------------------------------------------

_LINE_NUM_RE = re.compile(r"^(\s{0,4})(\d{1,5})(\s{1,4}|\t)(.*)$")


def strip_line_numbers(text: str, min_sequential: int = 5) -> str:
    """
    Remove sequential line numbers from the left margin.

    Only strips if at least *min_sequential* lines in a row have leading
    numbers that form an ascending sequence (gaps of up to 3 allowed).
    This avoids false positives on numbered lists, table rows, etc.

    Returns the text with line-number prefixes removed, or the original
    text unchanged if no sequential pattern is found.
    """
    lines = text.splitlines()
    if len(lines) < min_sequential:
        return text

    # Build a set of line indices that are inside fenced code blocks —
    # we must not strip intentional line numbers from code examples.
    fenced: set[int] = set()
    in_fence = False
    for idx, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            fenced.add(idx)
        elif in_fence:
            fenced.add(idx)

    # First pass: extract candidate line numbers (skip fenced lines)
    candidates: list[tuple[int, int, str]] = []  # (line_idx, number, rest_of_line)
    for idx, line in enumerate(lines):
        if idx in fenced:
            continue
        m = _LINE_NUM_RE.match(line)
        if m:
            candidates.append((idx, int(m.group(2)), m.group(4)))

    if len(candidates) < min_sequential:
        return text

    # Check for sequential pattern in candidates
    sequential_runs = _find_sequential_runs(candidates, min_sequential)

    if not sequential_runs:
        return text

    # Build set of line indices to strip
    strip_indices: set[int] = set()
    for run in sequential_runs:
        for line_idx, _num, _rest in run:
            strip_indices.add(line_idx)

    # Rebuild text
    result_lines = []
    for idx, line in enumerate(lines):
        if idx in strip_indices:
            m = _LINE_NUM_RE.match(line)
            if m:
                result_lines.append(m.group(4))  # keep content after number
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)

    return "\n".join(result_lines)


def _find_sequential_runs(
    candidates: list[tuple[int, int, str]],
    min_length: int,
) -> list[list[tuple[int, int, str]]]:
    """
    Find runs of candidates where the numbers are roughly ascending
    (each next number is 1-3 higher than the previous).
    """
    runs: list[list[tuple[int, int, str]]] = []
    current_run: list[tuple[int, int, str]] = [candidates[0]]

    for i in range(1, len(candidates)):
        prev_num = current_run[-1][1]
        curr_num = candidates[i][1]
        gap = curr_num - prev_num

        if 1 <= gap <= 3:
            current_run.append(candidates[i])
        else:
            if len(current_run) >= min_length:
                runs.append(current_run)
            current_run = [candidates[i]]

    if len(current_run) >= min_length:
        runs.append(current_run)

    return runs


# ---------------------------------------------------------------------------
# 4. Code Block Detection
# ---------------------------------------------------------------------------

# Patterns suggesting lines are source code
_CODE_PATTERNS = re.compile(
    r"(?:"
    r"^\s{4,}\S"                                 # 4+ space indent
    r"|^[\t]\S"                                   # tab-indented
    r"|import\s+[\w.]+"                           # import statements
    r"|from\s+[\w.]+\s+import"                    # from...import
    r"|def\s+\w+\s*\("                            # Python function
    r"|class\s+\w+[\s:(]"                         # class definition
    r"|function\s+\w+\s*\("                       # JS function
    r"|const\s+\w+\s*="                           # JS const
    r"|var\s+\w+\s*="                             # JS var
    r"|let\s+\w+\s*="                             # JS let
    r"|#include\s*[<\"]"                           # C include
    r"|public\s+(?:static|class|void|int|String)"  # Java
    r"|if\s*\(.+\)\s*\{"                          # C-style if
    r"|for\s*\(.+\)\s*\{"                         # C-style for
    r"|while\s*\(.+\)\s*\{"                       # C-style while
    r"|return\s+.+;"                              # return with semicolon
    r"|^\s*[{}];?\s*$"                             # brace-only lines
    r")",
    re.MULTILINE,
)

# Characters common in code but rare in prose
_CODE_CHARS = set("{}();[]<>=!&|^~@#$")


def detect_code_blocks_in_markdown(text: str) -> str:
    """
    Heuristic detection of code blocks in Markdown text.

    Scans for consecutive lines that look like source code based on:
      - Consistent 4+ space indentation
      - High density of code-specific punctuation
      - Pattern matches for common programming constructs

    Wraps detected blocks in ``` fences with a language hint if detectable.
    Skips content already inside ``` fences.
    """
    lines = text.split("\n")
    result_lines: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Already inside a fenced code block — pass through
        if line.strip().startswith("```"):
            result_lines.append(line)
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                result_lines.append(lines[i])
                i += 1
            if i < n:
                result_lines.append(lines[i])
                i += 1
            continue

        # Check if this starts a code-like block
        if _is_code_line(line):
            block_start = i
            while i < n and (_is_code_line(lines[i]) or lines[i].strip() == ""):
                i += 1
            block_end = i

            # Trim trailing empty lines
            while block_end > block_start and lines[block_end - 1].strip() == "":
                block_end -= 1

            code_lines = lines[block_start:block_end]
            non_empty = [l for l in code_lines if l.strip()]

            # Only wrap if we have at least 3 non-empty code lines
            if len(non_empty) >= 3:
                lang = _guess_language(non_empty)
                result_lines.append(f"```{lang}")
                for cl in code_lines:
                    result_lines.append(cl)
                result_lines.append("```")
            else:
                result_lines.extend(code_lines)
            continue

        result_lines.append(line)
        i += 1

    return "\n".join(result_lines)


def _is_code_line(line: str) -> bool:
    """Heuristic: does this single line look like code?"""
    stripped = line.strip()
    if not stripped:
        return False

    # 4+ space or tab indent with content
    if line.startswith("    ") or line.startswith("\t"):
        return True

    # Pattern match
    if _CODE_PATTERNS.search(stripped):
        return True

    # High code-character density
    if len(stripped) > 5:
        code_char_count = sum(1 for ch in stripped if ch in _CODE_CHARS)
        ratio = code_char_count / len(stripped)
        if ratio > 0.15:
            return True

    return False


def _guess_language(lines: list[str]) -> str:
    """Try to guess the programming language from code lines."""
    text = "\n".join(lines)
    if re.search(r'\bdef\s+\w+\s*\(|import\s+\w+|from\s+\w+\s+import', text):
        return "python"
    if re.search(r'function\s+\w+|const\s+\w+\s*=|=>\s*{|console\.log', text):
        return "javascript"
    if re.search(r'#include\s*[<"]|int\s+main\s*\(|printf\s*\(', text):
        return "c"
    if re.search(r'public\s+(?:static|class)|System\.out\.print', text):
        return "java"
    if re.search(r'<\w+[^>]*>.*</\w+>', text):
        return "html"
    if re.search(r'SELECT\s+.+\s+FROM|INSERT\s+INTO|CREATE\s+TABLE', text, re.IGNORECASE):
        return "sql"
    return ""


# ---------------------------------------------------------------------------
# 5. Footnote Handling
# ---------------------------------------------------------------------------

_FOOTNOTE_REF_RE = re.compile(
    r'(?<=[.,;:!?\"\'\])])(\d{1,3})(?=[\s.,;:)\]]|$)'
)

_FOOTNOTE_DEF_RE = re.compile(
    r'^(\d{1,3})[.\s)]+(.+)$',
    re.MULTILINE,
)


def detect_footnotes_in_markdown(text: str) -> str:
    """
    Detect footnote patterns in Markdown text and convert to standard
    Markdown footnote syntax: [^N] for references and [^N]: for definitions.

    Heuristic approach:
      1. Look for a "footnotes" or "notes" section near the end of the text.
      2. Parse numbered definitions (e.g., "1. Note text" or "1) Note text").
      3. Convert references in the body text to [^N] format.
      4. Append [^N]: definitions at the end.

    Only processes text if a clear footnote section is detected.
    """
    # Look for a footnote section header
    footnote_section = re.search(
        r'(?m)^#+\s*(?:foot\s*notes?|end\s*notes?|notes?)\s*$',
        text,
        re.IGNORECASE,
    )

    if not footnote_section:
        # Try detecting a cluster of numbered definitions at the end
        lines = text.rstrip().splitlines()
        if len(lines) < 5:
            return text

        # Check last 30% of lines for numbered definitions
        check_start = max(0, len(lines) - len(lines) // 3)
        definitions: dict[int, str] = {}
        def_start_line = None

        for idx in range(check_start, len(lines)):
            m = _FOOTNOTE_DEF_RE.match(lines[idx].strip())
            if m:
                num = int(m.group(1))
                if 1 <= num <= 200:
                    if def_start_line is None:
                        def_start_line = idx
                    definitions[num] = m.group(2).strip()

        if len(definitions) < 2:
            return text

        # Verify definitions are roughly sequential
        nums = sorted(definitions.keys())
        if nums[0] > 5 or (nums[-1] - nums[0]) > len(nums) * 3:
            return text  # Numbers too scattered to be footnotes

        # Build the result
        body_lines = lines[:def_start_line]
        body_text = "\n".join(body_lines)
    else:
        # Split at the footnote section header
        body_text = text[:footnote_section.start()].rstrip()
        footnote_text = text[footnote_section.end():]

        definitions = {}
        for m in _FOOTNOTE_DEF_RE.finditer(footnote_text):
            num = int(m.group(1))
            if 1 <= num <= 200:
                definitions[num] = m.group(2).strip()

        if not definitions:
            return text

    # Convert references in body: bare numbers that match our definitions
    def replace_ref(match):
        num = int(match.group(1))
        if num in definitions:
            return f"[^{num}]"
        return match.group(0)

    body_text = _FOOTNOTE_REF_RE.sub(replace_ref, body_text)

    # Append footnote definitions
    footnote_defs = []
    for num in sorted(definitions.keys()):
        footnote_defs.append(f"[^{num}]: {definitions[num]}")

    return body_text + "\n\n" + "\n".join(footnote_defs)


# ---------------------------------------------------------------------------
# 6. Equation Detection
# ---------------------------------------------------------------------------

_GREEK_UNICODE = set(
    "αβγδεζηθικλμνξοπρστυφχψω"
    "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
)

# Math operator / symbol characters
_MATH_SYMBOLS = set("±×÷≠≈≤≥∞∑∏∫∂∇√∈∉⊂⊃⊆⊇∪∩∧∨¬∀∃⟨⟩→←↔⇒⇐⇔")

def detect_equations(text: str) -> str:
    """
    Detect mathematical content and wrap in LaTeX delimiters.

    Conservative approach:
      - Only wraps content with clear mathematical signals (Greek letters,
        math operators, known function names, subscript/superscript patterns).
      - Skips content already inside code blocks (``` fences).
      - Inline math → $...$
      - Display math (standalone line) → $$...$$

    Returns the text with detected equations wrapped in LaTeX delimiters.
    """
    lines = text.split("\n")
    result: list[str] = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Track code blocks — never modify content inside them
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        # Skip lines already containing $ delimiters (already formatted)
        if "$" in line:
            result.append(line)
            continue

        # Check for display math (entire line is a formula)
        if _is_display_math(stripped):
            result.append(f"$${stripped}$$")
            continue

        # Check for inline math expressions and wrap them
        line = _wrap_inline_math(line)
        result.append(line)

    return "\n".join(result)


def _is_display_math(line: str) -> bool:
    """Check if an entire line looks like a standalone math expression."""
    if not line or len(line) < 3:
        return False

    # Count math-indicative characters
    math_chars = sum(1 for ch in line if ch in _MATH_SYMBOLS or ch in _GREEK_UNICODE)
    has_operators = bool(re.search(r'[=<>≠≈≤≥+\-*/^]', line))
    has_greek = bool(_GREEK_UNICODE.intersection(set(line)))
    has_latex_cmd = bool(re.search(r'\\[a-zA-Z]+', line))

    # Must have significant math content relative to line length
    alpha_count = sum(1 for ch in line if ch.isalpha())
    total = len(line.replace(" ", ""))

    if total == 0:
        return False

    # Heuristic: line must have math operators and be short-to-medium length
    # (display equations are rarely > 120 chars of just math)
    if has_operators and total < 120:
        if has_greek or has_latex_cmd:
            return True
        if math_chars > 0 and math_chars / total > 0.1:
            return True
        # Pattern: variable = expression with operators
        if re.match(r'^[A-Za-z_]\w*\s*=\s*.*[+\-*/^]', line):
            # But not assignments like "x = get_value()" or prose
            if not re.search(r'[a-z]{4,}\(', line):  # no function calls with long names
                return True

    return False


def _wrap_inline_math(line: str) -> str:
    """Find and wrap inline math expressions in a line of text."""
    # Look for patterns like Greek Unicode chars surrounded by text
    # or short mathematical subexpressions
    result = line

    # Wrap isolated Greek Unicode characters or short math expressions
    # Pattern: word boundary, math expression, word boundary
    def _maybe_wrap(match):
        expr = match.group(0)
        # Don't wrap if it's too long (probably not math)
        if len(expr) > 40:
            return expr
        return f"${expr}$"

    # Greek Unicode within text
    if _GREEK_UNICODE.intersection(set(result)):
        result = re.sub(
            r'(?<!\$)([αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ](?:\s*[=<>+\-*/^_]\s*[a-zA-Z0-9αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ]*)*)(?!\$)',
            _maybe_wrap,
            result,
        )

    return result


# ---------------------------------------------------------------------------
# Pipeline runner (convenience for callers)
# ---------------------------------------------------------------------------

def run_pipeline(
    pages: list[str],
    *,
    do_remove_headers_footers: bool = True,
    do_skip_blank_pages: bool = True,
    do_strip_line_numbers: bool = False,
    do_detect_code_blocks: bool = False,
    do_detect_footnotes: bool = False,
    do_detect_equations: bool = False,
) -> list[str]:
    """
    Run the enabled post-processors in the correct order on a list of
    per-page text strings. Returns the cleaned list.

    Processing order:
      1. Header/footer removal  (cross-page analysis)
      2. Blank page filtering   (per-page threshold)
      3. Line number stripping  (per-page regex)
      4. Code block detection   (per-page heuristic)
      5. Footnote detection     (per-page regex)
      6. Equation detection     (per-page heuristic) — runs last to avoid
         wrapping code or footnotes as math

    Callers that have a single monolithic string rather than per-page
    text should wrap it in a one-element list and unwrap afterward.
    """
    result = list(pages)

    if do_remove_headers_footers:
        result = remove_headers_footers(result)

    if do_skip_blank_pages:
        result = filter_blank_pages(result)

    # Detect code blocks BEFORE stripping line numbers so that intentional
    # line numbers inside code examples are preserved.
    if do_detect_code_blocks:
        result = [detect_code_blocks_in_markdown(p) for p in result]

    if do_strip_line_numbers:
        result = [strip_line_numbers(p) for p in result]

    if do_detect_footnotes:
        result = [detect_footnotes_in_markdown(p) for p in result]

    if do_detect_equations:
        result = [detect_equations(p) for p in result]

    return result
