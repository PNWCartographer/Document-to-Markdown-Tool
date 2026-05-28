"""
Shared helpers for ensemble OCR — IOU-based word alignment and merging.

Used by both ocr_engine.py (regular pipeline) and ocrmypdf_rapidocr.py
(Searchable PDF plugin) to combine results from RapidOCR and Tesseract.
"""

from dataclasses import dataclass


@dataclass
class WordBox:
    """A single word with bounding box and confidence."""
    text: str
    confidence: float
    left: float
    top: float
    right: float
    bottom: float
    engine: str = ""

    @property
    def cx(self) -> float:
        return (self.left + self.right) / 2

    @property
    def cy(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top


def normalize_bbox(bbox) -> tuple[float, float, float, float]:
    """Convert any bbox format to (left, top, right, bottom).

    Handles:
    - 4-point polygon: [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
    - Rectangle dict: {"left": L, "top": T, "width": W, "height": H}
    - Rectangle tuple: (left, top, right, bottom) — returned as-is
    """
    if isinstance(bbox, dict):
        l = float(bbox["left"])
        t = float(bbox["top"])
        return (l, t, l + float(bbox["width"]), t + float(bbox["height"]))

    if isinstance(bbox, (list, tuple)):
        if len(bbox) == 4 and isinstance(bbox[0], (int, float)):
            return tuple(float(v) for v in bbox)
        # Polygon — find bounding rectangle
        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        return (min(xs), min(ys), max(xs), max(ys))

    # ndarray
    if hasattr(bbox, "tolist"):
        return normalize_bbox(bbox.tolist())

    raise ValueError(f"Unsupported bbox format: {type(bbox)}")


def compute_iou(a: tuple, b: tuple) -> float:
    """Intersection-over-union of two (left, top, right, bottom) rectangles."""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    inter = (x2 - x1) * (y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter

    if union <= 0:
        return 0.0
    return inter / union


def merge_word_results(
    words_a: list[WordBox],
    words_b: list[WordBox],
    iou_threshold: float = 0.3,
) -> list[WordBox]:
    """Merge two sets of OCR word detections, keeping the higher-confidence word
    for each spatially matched pair.

    Unmatched words from either set are included as-is.
    """
    if not words_a:
        return list(words_b)
    if not words_b:
        return list(words_a)

    used_b = set()
    winners: list[WordBox] = []

    for wa in words_a:
        best_iou = 0.0
        best_idx = -1
        bbox_a = (wa.left, wa.top, wa.right, wa.bottom)

        for j, wb in enumerate(words_b):
            if j in used_b:
                continue
            bbox_b = (wb.left, wb.top, wb.right, wb.bottom)
            iou = compute_iou(bbox_a, bbox_b)
            if iou > best_iou:
                best_iou = iou
                best_idx = j

        if best_iou >= iou_threshold and best_idx >= 0:
            used_b.add(best_idx)
            wb = words_b[best_idx]
            winners.append(wa if wa.confidence >= wb.confidence else wb)
        else:
            winners.append(wa)

    for j, wb in enumerate(words_b):
        if j not in used_b:
            winners.append(wb)

    return winners


def sort_into_lines(
    words: list[WordBox],
    line_height_factor: float = 0.5,
) -> list[list[WordBox]]:
    """Group words into lines by Y-proximity, then sort left-to-right within each line."""
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: (w.cy, w.cx))

    lines: list[list[WordBox]] = []
    current_line: list[WordBox] = [sorted_words[0]]
    current_cy = sorted_words[0].cy
    current_h = sorted_words[0].height or 10

    for w in sorted_words[1:]:
        if abs(w.cy - current_cy) <= current_h * line_height_factor:
            current_line.append(w)
        else:
            lines.append(sorted(current_line, key=lambda w: w.cx))
            current_line = [w]
            current_cy = w.cy
            current_h = w.height or 10

    if current_line:
        lines.append(sorted(current_line, key=lambda w: w.cx))

    return lines


def words_to_text(words: list[WordBox]) -> tuple[list[str], list[float]]:
    """Convert merged words to lines of text and per-line confidence scores."""
    lines_of_words = sort_into_lines(words)
    text_lines = []
    confidences = []

    for line_words in lines_of_words:
        text = " ".join(w.text for w in line_words if w.text.strip())
        if text.strip():
            text_lines.append(text)
            avg_conf = sum(w.confidence for w in line_words) / len(line_words)
            confidences.append(avg_conf)

    return text_lines, confidences
