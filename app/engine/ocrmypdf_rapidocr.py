"""
ocrmypdf plugin that provides RapidOCR as the OCR engine.

Routes OCR through ONNX Runtime instead of Tesseract, enabling GPU
acceleration via CUDA (NVIDIA), DirectML (AMD/Intel on Windows),
CoreML (macOS), or CPU fallback.

Usage with ocrmypdf Python API:
    from app.engine import ocrmypdf_rapidocr
    ocrmypdf.ocr(input_pdf, output_pdf, plugins=[ocrmypdf_rapidocr])
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Set

import ocrmypdf

log = logging.getLogger(__name__)


@ocrmypdf.hookimpl
def get_ocr_engine(options=None):
    return RapidOcrEngine()


class RapidOcrEngine(ocrmypdf.OcrEngine):

    @staticmethod
    def version() -> str:
        try:
            from importlib.metadata import version as pkg_version
            return pkg_version("rapidocr-onnxruntime")
        except Exception:
            return "unknown"

    @staticmethod
    def creator_tag(options) -> str:
        return f"RapidOCR (ONNX Runtime) {RapidOcrEngine.version()}"

    def __str__(self) -> str:
        return f"RapidOCR {self.version()}"

    @staticmethod
    def languages(options) -> Set[str]:
        return {
            "eng", "fra", "deu", "spa", "ita", "por", "nld",
            "chi_sim", "chi_tra", "jpn", "kor", "ara", "rus",
        }

    @staticmethod
    def get_orientation(
        input_file: Path, options,
    ) -> ocrmypdf.OrientationConfidence:
        return ocrmypdf.OrientationConfidence(angle=0, confidence=0.0)

    @staticmethod
    def generate_hocr(
        input_file: Path,
        output_hocr: Path,
        output_text: Path,
        options,
    ) -> None:
        from PIL import Image
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR

        img = Image.open(input_file)
        width, height = img.size

        engine = RapidOCR()
        img_array = np.array(img.convert("RGB"))
        raw, _ = engine(img_array)

        lines_text = []
        word_elements = []
        word_id = 0

        if raw:
            for item in raw:
                if not item or len(item) < 3:
                    continue
                bbox = item[0]
                text = str(item[1]).strip()
                conf = float(item[2])
                if not text:
                    continue
                if not (0.0 <= conf <= 1.0):
                    conf = 0.5

                bbox_list = bbox.tolist() if hasattr(bbox, "tolist") else list(bbox)
                left = int(min(p[0] for p in bbox_list))
                top = int(min(p[1] for p in bbox_list))
                right = int(max(p[0] for p in bbox_list))
                bottom = int(max(p[1] for p in bbox_list))

                left = max(0, left)
                top = max(0, top)
                right = min(width, right)
                bottom = min(height, bottom)

                if right <= left or bottom <= top:
                    continue

                wconf = int(conf * 100)
                word_id += 1
                word_elements.append(
                    f'       <span class="ocrx_word" id="word_{word_id}" '
                    f'title="bbox {left} {top} {right} {bottom}; '
                    f'x_wconf {wconf}">{_hocr_escape(text)}</span>'
                )
                lines_text.append(text)

        hocr = _build_hocr(width, height, word_elements)
        output_hocr.write_text(hocr, encoding="utf-8")
        output_text.write_text("\n".join(lines_text), encoding="utf-8")

    @staticmethod
    def generate_pdf(
        input_file: Path,
        output_pdf: Path,
        output_text: Path,
        options,
    ) -> None:
        raise NotImplementedError("Use generate_hocr instead")


def _hocr_escape(text: str) -> str:
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_hocr(page_width: int, page_height: int, word_elements: list[str]) -> str:
    words_block = "\n".join(word_elements)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE html PUBLIC "
        '"-//W3C//DTD XHTML 1.0 Transitional//EN"\n'
        '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n'
        "<head>\n"
        '  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n'
        "  <title>RapidOCR Output</title>\n"
        "</head>\n"
        "<body>\n"
        f'  <div class="ocr_page" id="page_1" '
        f'title="bbox 0 0 {page_width} {page_height}">\n'
        f'    <div class="ocr_carea" id="block_1" '
        f'title="bbox 0 0 {page_width} {page_height}">\n'
        f'      <p class="ocr_par" id="par_1">\n'
        f"{words_block}\n"
        f"      </p>\n"
        f"    </div>\n"
        f"  </div>\n"
        "</body>\n"
        "</html>\n"
    )
