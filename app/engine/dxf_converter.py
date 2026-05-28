"""
DXF (AutoCAD Drawing Exchange Format) to Markdown converter.

Conversion approach:
  - Title block metadata extracted from INSERT block attributes → YAML front matter.
  - SVG preview rendered via ezdxf drawing add-on → embedded in Markdown.
  - Layer listing → Markdown table.
  - TEXT / MTEXT entities → organized by layer, sorted spatially.
  - DIMENSION entities → measurement table.
  - MLEADER / MULTILEADER annotations → callout table.
  - ACAD_TABLE entities → Markdown tables.
  - XREFs and font substitutions → warnings.

Dependency: ezdxf >= 1.4.0

Cross-platform: ezdxf is pure Python (optional Cython). No system
libraries or platform-specific dependencies required.
"""

import os
import re
from typing import Optional, Callable

from .confidence import ConfidenceResult
from .markdown_writer import (
    ConversionOutput,
    assets_dir_for,
    assets_rel_prefix_for,
    rows_to_markdown_table,
)
from .logger import ConversionLogger


# ── Common title-block attribute tags ─────────────────────────
# These are the conventional ATTDEF tag names found in standard
# title blocks. The mapping normalises tag → human label.
_TITLE_BLOCK_TAGS = {
    # Drawing identification
    "TITLE":            "Title",
    "DWG_TITLE":        "Title",
    "DRAWING_TITLE":    "Title",
    "DWG_NO":           "Drawing Number",
    "DRAWING_NO":       "Drawing Number",
    "DRAWING_NUMBER":   "Drawing Number",
    "DWG_NUM":          "Drawing Number",
    "SHEET_NO":         "Sheet",
    "SHEET":            "Sheet",
    "SHEET_NUMBER":     "Sheet",
    "SHEETS":           "Total Sheets",
    "TOTAL_SHEETS":     "Total Sheets",
    # Revision
    "REV":              "Revision",
    "REVISION":         "Revision",
    "REV_NO":           "Revision",
    "REV_DATE":         "Revision Date",
    # People
    "DRAWN_BY":         "Drawn By",
    "DRAWN":            "Drawn By",
    "DRAFTER":          "Drawn By",
    "CHECKED_BY":       "Checked By",
    "CHECKED":          "Checked By",
    "APPROVED_BY":      "Approved By",
    "APPROVED":         "Approved By",
    "DESIGNER":         "Designer",
    "ENGINEER":         "Engineer",
    # Dates
    "DATE":             "Date",
    "DWG_DATE":         "Date",
    "DRAWING_DATE":     "Date",
    # Organisation
    "COMPANY":          "Company",
    "CLIENT":           "Client",
    "PROJECT":          "Project",
    "PROJECT_NAME":     "Project",
    "PROJECT_NO":       "Project Number",
    "PROJECT_NUMBER":   "Project Number",
    # Scale / units
    "SCALE":            "Scale",
    "UNITS":            "Units",
    # Description
    "DESCRIPTION":      "Description",
    "DESC":             "Description",
    "NOTES":            "Notes",
}


def convert(
    source_file: str,
    alias: str = "",
    output_root: str = "",
    preserve_images: bool = True,
    use_subfolder: bool = True,
    render_svg: bool = True,
    logger: Optional[ConversionLogger] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> ConversionOutput:
    """Convert a .dxf file to structured Markdown."""
    output = ConversionOutput(source_file=source_file, alias=alias)
    confidence = ConfidenceResult(source_file=source_file)
    output.confidence = confidence

    try:
        import ezdxf
    except ImportError as e:
        confidence.text_extraction = "Failed"
        confidence.overall = "Failed"
        confidence.add_warning(f"ezdxf not installed: {e}")
        return output

    output.engine_used = "ezdxf"

    def log_info(msg):
        if logger:
            logger.info(msg)

    def log_warn(msg):
        if logger:
            logger.warning(msg)
        confidence.add_warning(msg)

    def progress(p):
        if progress_callback:
            progress_callback(p)

    log_info(f"DXF converter started | file={os.path.basename(source_file)}")
    progress(0.05)

    # ── Load DXF ─────────────────────────────────────────────
    doc = None
    try:
        doc = ezdxf.readfile(source_file)
    except Exception:
        pass

    # Fallback: try ezdxf.recover for damaged / non-standard files
    if doc is None:
        try:
            from ezdxf import recover
            doc, auditor = recover.readfile(source_file)
            if auditor.has_errors:
                log_warn(f"DXF recovery fixed {len(auditor.errors)} error(s).")
        except Exception as e:
            log_warn(f"Failed to read DXF file: {e}")
            confidence.text_extraction = "Failed"
            confidence.overall = "Failed"
            return output

    dxf_version = doc.dxfversion if hasattr(doc, "dxfversion") else "unknown"
    log_info(f"DXF loaded | version={dxf_version}")
    progress(0.15)

    msp = doc.modelspace()

    # ── Assets directory ─────────────────────────────────────
    assets_dir = None
    rel_prefix = "assets/"
    if preserve_images and output_root:
        assets_dir = assets_dir_for(source_file, output_root, alias, use_subfolder)
        rel_prefix = assets_rel_prefix_for(source_file, alias, use_subfolder)
        os.makedirs(assets_dir, exist_ok=True)

    # ── 1. Title block extraction ────────────────────────────
    progress(0.20)
    title_block = _extract_title_block(doc, msp)
    log_info(f"Title block: {len(title_block)} attributes found")

    # ── 2. Layer listing ─────────────────────────────────────
    progress(0.30)
    layer_info = _extract_layers(doc, msp)
    log_info(f"Layers: {len(layer_info)} layers")

    # ── 3. Text entities ─────────────────────────────────────
    progress(0.40)
    text_by_layer = _extract_text_entities(msp)
    total_text = sum(len(v) for v in text_by_layer.values())
    log_info(f"Text entities: {total_text} across {len(text_by_layer)} layers")

    # ── 4. Dimensions ────────────────────────────────────────
    progress(0.50)
    dimensions = _extract_dimensions(msp)
    log_info(f"Dimensions: {len(dimensions)} found")

    # ── 5. Leaders / callouts ────────────────────────────────
    progress(0.55)
    leaders = _extract_leaders(msp)
    log_info(f"Leaders/callouts: {len(leaders)} found")

    # ── 6. Tables ────────────────────────────────────────────
    progress(0.60)
    tables = _extract_tables(msp)
    log_info(f"Tables: {len(tables)} found")

    # ── 7. Paper-space content ───────────────────────────────
    progress(0.65)
    paperspace_text = _extract_paperspace_text(doc)

    # ── 8. SVG preview ───────────────────────────────────────
    progress(0.70)
    svg_ref = ""
    if assets_dir and render_svg:
        svg_ref = _render_svg_preview(doc, msp, assets_dir, rel_prefix,
                                       source_file, alias, log_info, log_warn)
    elif not render_svg:
        log_info("SVG preview disabled by settings — skipping render.")

    # ── 9. Detect XREFs ──────────────────────────────────────
    progress(0.80)
    _detect_xrefs(doc, log_warn)

    # ── Build Markdown sections ──────────────────────────────
    progress(0.85)

    stem = alias if alias else os.path.splitext(os.path.basename(source_file))[0]

    # Title / heading
    drawing_title = title_block.get("Title", stem)
    drawing_number = title_block.get("Drawing Number", "")
    if drawing_number:
        main_heading = f"# {drawing_number} — {drawing_title}"
    else:
        main_heading = f"# {drawing_title}"

    output.add_section(heading=main_heading, body="")

    # Preview image
    if svg_ref:
        output.add_section(
            heading="## Drawing Preview",
            body=f"![Drawing Preview]({svg_ref})",
        )

    # Title block table
    if title_block:
        rows = [[k, v] for k, v in title_block.items()]
        table_md = rows_to_markdown_table(["Field", "Value"], rows)
        output.add_section(heading="## Title Block", body=table_md)

    # Layer table
    if layer_info:
        rows = [[l["name"], l["color"], str(l["entities"]), l["status"]]
                for l in layer_info]
        table_md = rows_to_markdown_table(
            ["Layer", "Color", "Entities", "Status"], rows)
        output.add_section(heading="## Layers", body=table_md)

    # Dimensions table
    if dimensions:
        rows = [[d["text"], d["value"], d["layer"]] for d in dimensions]
        table_md = rows_to_markdown_table(
            ["Dimension", "Value", "Layer"], rows)
        output.add_section(heading="## Dimensions", body=table_md)

    # Leaders / callouts table
    if leaders:
        rows = [[ld["text"], ld["layer"]] for ld in leaders]
        table_md = rows_to_markdown_table(["Annotation", "Layer"], rows)
        output.add_section(heading="## Annotations", body=table_md)

    # Tables from drawing
    for idx, tbl in enumerate(tables, 1):
        if tbl and len(tbl) > 1:
            headers = tbl[0]
            data = tbl[1:]
            table_md = rows_to_markdown_table(headers, data)
            output.add_section(
                heading=f"## Table {idx}",
                body=table_md,
            )

    # Text by layer
    if text_by_layer:
        body_parts = []
        for layer_name, texts in sorted(text_by_layer.items()):
            body_parts.append(f"### Layer: {layer_name}\n")
            for t in texts:
                content = t["text"].strip()
                if content:
                    body_parts.append(f"- {content}")
            body_parts.append("")
        output.add_section(
            heading="## Text Content",
            body="\n".join(body_parts),
        )

    # Paper-space text
    if paperspace_text:
        body_parts = []
        for layout_name, texts in paperspace_text.items():
            if texts:
                body_parts.append(f"### Layout: {layout_name}\n")
                for t in texts:
                    body_parts.append(f"- {t}")
                body_parts.append("")
        if body_parts:
            output.add_section(
                heading="## Paper Space Notes",
                body="\n".join(body_parts),
            )

    # ── Confidence scoring ───────────────────────────────────
    progress(0.95)
    if total_text > 0:
        confidence.text_extraction = "High"
    elif title_block:
        confidence.text_extraction = "Medium"
        confidence.add_note("Few text entities found; title block attributes extracted.")
    else:
        confidence.text_extraction = "Low"
        confidence.add_warning("No text content found in drawing.")

    confidence.table_structure = "High" if dimensions or tables else "N/A"
    confidence.image_extraction = "High" if svg_ref else "Low"
    confidence.image_placement = "High" if svg_ref else "N/A"
    confidence.document_order = "High"
    confidence.ocr_confidence = "N/A"
    confidence.derive_overall()

    # Store title block metadata for front-matter enrichment
    output.metadata["dxf_title_block"] = title_block

    progress(1.0)
    log_info("DXF conversion complete.")
    return output


# =====================================================================
# Extraction helpers
# =====================================================================

def _extract_title_block(doc, msp) -> dict[str, str]:
    """
    Extract title block attributes from INSERT entities.

    Searches both model space and paper space for block references
    containing ATTRIBs whose tags match known title-block field names.
    """
    found: dict[str, str] = {}

    # Search all layouts (model + paper spaces)
    layouts = [msp]
    try:
        for layout in doc.layouts:
            if layout.name != "Model":
                layouts.append(layout)
    except Exception:
        pass

    for layout in layouts:
        try:
            for insert in layout.query("INSERT"):
                for attrib in insert.attribs:
                    tag = attrib.dxf.tag.upper().strip()
                    value = attrib.dxf.text.strip()
                    if not value:
                        continue
                    label = _TITLE_BLOCK_TAGS.get(tag)
                    if label and label not in found:
                        found[label] = value
        except Exception:
            continue

    return found


def _extract_layers(doc, msp) -> list[dict]:
    """List all layers with colour and entity counts."""
    # Count entities per layer in model space
    # Note: some DXF exporters (IVREAD, mesh tools) pad layer names with
    # leading whitespace (e.g. "  0" instead of "0").  We strip to match
    # the canonical name stored in the layer table.
    entity_counts: dict[str, int] = {}
    try:
        for entity in msp:
            layer = entity.dxf.layer.strip() if hasattr(entity.dxf, "layer") else "0"
            entity_counts[layer] = entity_counts.get(layer, 0) + 1
    except Exception:
        pass

    # Fallback: some minimal DXF files have empty TABLES/BLOCKS sections.
    # Entities may not enumerate through msp; count from doc.entities.
    if not entity_counts:
        try:
            for entity in doc.entities:
                layer = entity.dxf.layer.strip() if hasattr(entity.dxf, "layer") else "0"
                entity_counts[layer] = entity_counts.get(layer, 0) + 1
        except Exception:
            pass

    layers = []
    _COLOR_NAMES = {
        1: "Red", 2: "Yellow", 3: "Green", 4: "Cyan",
        5: "Blue", 6: "Magenta", 7: "White/Black",
    }
    try:
        for layer in doc.layers:
            name = layer.dxf.name
            color_idx = layer.dxf.color
            color_name = _COLOR_NAMES.get(color_idx, str(color_idx))
            status_parts = []
            if not layer.is_on():
                status_parts.append("Off")
            if layer.is_frozen():
                status_parts.append("Frozen")
            if layer.is_locked():
                status_parts.append("Locked")
            status = ", ".join(status_parts) if status_parts else "Active"

            layers.append({
                "name": name,
                "color": color_name,
                "entities": entity_counts.get(name, 0),
                "status": status,
            })
    except Exception:
        pass

    # Sort: layers with entities first, then alphabetical
    layers.sort(key=lambda l: (-l["entities"], l["name"].lower()))
    return layers


def _extract_text_entities(msp) -> dict[str, list[dict]]:
    """
    Extract TEXT and MTEXT entities, grouped by layer.

    Each entry: {"text": str, "x": float, "y": float}
    Entries within each layer are sorted top-to-bottom, left-to-right.
    """
    by_layer: dict[str, list[dict]] = {}

    try:
        for text in msp.query("TEXT"):
            layer = text.dxf.layer.strip()
            content = text.dxf.text
            x = text.dxf.insert.x if hasattr(text.dxf, "insert") else 0
            y = text.dxf.insert.y if hasattr(text.dxf, "insert") else 0
            by_layer.setdefault(layer, []).append({
                "text": content, "x": x, "y": y,
            })
    except Exception:
        pass

    try:
        for mtext in msp.query("MTEXT"):
            layer = mtext.dxf.layer.strip()
            content = mtext.plain_text()
            x = mtext.dxf.insert.x if hasattr(mtext.dxf, "insert") else 0
            y = mtext.dxf.insert.y if hasattr(mtext.dxf, "insert") else 0
            by_layer.setdefault(layer, []).append({
                "text": content, "x": x, "y": y,
            })
    except Exception:
        pass

    # Sort within each layer: top-to-bottom (descending Y), then left-to-right
    for entries in by_layer.values():
        entries.sort(key=lambda e: (-e["y"], e["x"]))

    return by_layer


def _extract_dimensions(msp) -> list[dict]:
    """Extract DIMENSION entities with measurement values."""
    dims = []
    try:
        for dim in msp.query("DIMENSION"):
            layer = dim.dxf.layer
            # Get the numeric measurement
            try:
                measurement = dim.get_measurement()
                value_str = f"{measurement:.4g}"
            except Exception:
                value_str = "—"

            # Try to get displayed text
            display_text = ""
            try:
                override = dim.dxf.text
                if override and override.strip() and override.strip() != "<>":
                    display_text = override.strip()
            except Exception:
                pass

            if not display_text:
                # Try extracting from the geometry block
                try:
                    block = dim.get_geometry_block()
                    if block:
                        for entity in block.query("TEXT MTEXT"):
                            txt = (entity.dxf.text if hasattr(entity.dxf, "text")
                                   else "")
                            if txt.strip():
                                display_text = txt.strip()
                                break
                except Exception:
                    pass

            if not display_text:
                display_text = value_str

            dims.append({
                "text": display_text,
                "value": value_str,
                "layer": layer,
            })
    except Exception:
        pass

    return dims


def _extract_leaders(msp) -> list[dict]:
    """Extract LEADER and MLEADER annotation text."""
    leaders = []

    # MLEADER / MULTILEADER
    try:
        for mleader in msp.query("MLEADER MULTILEADER"):
            layer = mleader.dxf.layer
            text = ""
            try:
                ctx = mleader.context
                if hasattr(ctx, "mtext") and ctx.mtext:
                    text = ctx.mtext.default_content or ""
            except Exception:
                pass

            # Try block-based leaders
            if not text:
                try:
                    for attrib in mleader.block_attribs:
                        if hasattr(attrib, "text") and attrib.text:
                            text = attrib.text
                            break
                except Exception:
                    pass

            if text.strip():
                leaders.append({"text": text.strip(), "layer": layer})
    except Exception:
        pass

    return leaders


def _extract_tables(msp) -> list[list[list[str]]]:
    """Extract ACAD_TABLE entities as lists of rows."""
    tables = []
    try:
        for table_entity in msp.query("ACAD_TABLE"):
            try:
                rows = []
                for row_idx in range(table_entity.dxf.rows):
                    row = []
                    for col_idx in range(table_entity.dxf.cols):
                        try:
                            cell = table_entity.cell(row_idx, col_idx)
                            text = cell.text if hasattr(cell, "text") else ""
                            row.append(str(text).strip())
                        except Exception:
                            row.append("")
                    rows.append(row)
                if rows:
                    tables.append(rows)
            except Exception:
                continue
    except Exception:
        pass

    return tables


def _extract_paperspace_text(doc) -> dict[str, list[str]]:
    """Extract text from all paper-space layouts."""
    result: dict[str, list[str]] = {}
    try:
        for layout in doc.layouts:
            if layout.name == "Model":
                continue
            texts = []
            try:
                for text in layout.query("TEXT"):
                    content = text.dxf.text.strip()
                    if content:
                        texts.append(content)
                for mtext in layout.query("MTEXT"):
                    content = mtext.plain_text().strip()
                    if content:
                        texts.append(content)
            except Exception:
                continue
            if texts:
                result[layout.name] = texts
    except Exception:
        pass

    return result


def _render_svg_preview(
    doc, msp, assets_dir: str, rel_prefix: str,
    source_file: str, alias: str,
    log_info, log_warn,
) -> str:
    """
    Render the modelspace to a preview image and save to assets.

    Pipeline:
      1. Render DXF → SVG via ezdxf SVGBackend
      2. Fix SVG dimensions and stroke widths for display
      3. Convert SVG → PNG via PyMuPDF (fitz) for Markdown compatibility
      4. Save both SVG (vector) and PNG (raster) to assets
      5. Return the PNG path (universal Markdown image support)

    Falls back to SVG-only if PyMuPDF is unavailable.
    """
    try:
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing import svg, layout

        ctx = RenderContext(doc)
        backend = svg.SVGBackend()
        frontend = Frontend(ctx, backend)
        frontend.draw_layout(msp)

        # Auto-size page
        page = layout.Page(0, 0, layout.Units.mm)
        svg_string = backend.get_string(page)

        # Post-process: fix dimensions and stroke widths for display
        svg_string = _fix_svg_display(svg_string)

        stem = alias if alias else os.path.splitext(os.path.basename(source_file))[0]

        # Save SVG (vector quality, kept for reference)
        svg_filename = f"{stem}_preview.svg"
        svg_path = os.path.join(assets_dir, svg_filename)
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(svg_string)
        log_info(f"SVG preview saved: {svg_filename}")

        # Convert SVG → PNG via PyMuPDF for Markdown compatibility
        png_ref = _svg_to_png(svg_path, assets_dir, rel_prefix, stem,
                              log_info, log_warn)
        if png_ref:
            return png_ref

        # Fallback: reference the SVG directly
        log_info("PyMuPDF SVG→PNG conversion unavailable; using SVG reference.")
        return f"{rel_prefix}{svg_filename}"

    except ImportError:
        log_warn("ezdxf drawing add-on not available; skipping drawing preview.")
        return ""
    except Exception as e:
        log_warn(f"Drawing preview rendering failed: {e}")
        return ""


def _inline_svg_styles(svg_string: str) -> str:
    """
    Convert CSS class-based styles to inline attributes on each element.

    ezdxf SVGBackend generates styles like:
        <defs><style>.C1 {stroke: #fff; stroke-width: 2500;}</style></defs>
        <path class="C1" d="..."/>

    PyMuPDF's SVG renderer does not support CSS class selectors, so paths
    render invisible.  This function parses the <style> block, extracts
    each class's properties, and writes them as inline style="" attributes.
    """
    # Extract all CSS class definitions from <style> block
    style_match = re.search(r'<style>(.*?)</style>', svg_string, re.DOTALL)
    if not style_match:
        return svg_string

    style_text = style_match.group(1)

    # Parse class rules:  .C1 { prop: val; prop: val; }
    class_styles: dict[str, str] = {}
    for m in re.finditer(r'\.(\w+)\s*\{([^}]*)\}', style_text):
        class_name = m.group(1)
        props = m.group(2).strip()
        class_styles[class_name] = props

    if not class_styles:
        return svg_string

    # Replace class="Cn" with style="..." on every element
    def _replace_class(match):
        class_name = match.group(1)
        if class_name in class_styles:
            return f'style="{class_styles[class_name]}"'
        return match.group(0)

    svg_string = re.sub(r'class="(\w+)"', _replace_class, svg_string)

    return svg_string


def _svg_to_png(
    svg_path: str, assets_dir: str, rel_prefix: str,
    stem: str, log_info, log_warn,
) -> str:
    """Convert an SVG file to PNG using PyMuPDF (fitz). Return relative path or ''."""
    try:
        import fitz

        # Read SVG and inline CSS class styles for PyMuPDF compatibility
        with open(svg_path, "r", encoding="utf-8") as fh:
            svg_string = fh.read()
        svg_inlined = _inline_svg_styles(svg_string)

        # Open from string (PyMuPDF can open SVG from bytes)
        svg_doc = fitz.open(stream=svg_inlined.encode("utf-8"), filetype="svg")
        try:
            page = svg_doc[0]
            # Render at 150 DPI for crisp output without excessive file size
            pix = page.get_pixmap(dpi=150)

            png_filename = f"{stem}_preview.png"
            png_path = os.path.join(assets_dir, png_filename)
            pix.save(png_path)
        finally:
            svg_doc.close()

        log_info(f"PNG preview saved: {png_filename} "
                 f"({pix.width}x{pix.height}px)")
        return f"{rel_prefix}{png_filename}"

    except ImportError:
        return ""
    except Exception as e:
        log_warn(f"SVG→PNG conversion failed: {e}")
        return ""


def _fix_svg_display(svg_string: str) -> str:
    """
    Fix SVG dimensions and stroke widths for proper display.

    ezdxf SVGBackend sets width/height in mm matching the DXF model units.
    A 1-unit cube produces a 1mm-wide SVG (invisible in Markdown viewers).
    Stroke widths are also proportional to model units, producing strokes
    that can be 25–250% of the viewport width.

    This function:
      1. Adds 3% padding to the viewBox so geometry at the boundary
         isn't clipped (common for 3D projections where edges land
         exactly on the extents).
      2. Replaces width/height with reasonable pixel values (800px wide)
      3. Normalizes stroke-width to ~0.25% of viewBox for clean thin lines
    """
    # Extract viewBox dimensions
    vb_match = re.search(r'viewBox="([^"]*)"', svg_string)
    if not vb_match:
        return svg_string

    vb_parts = vb_match.group(1).split()
    if len(vb_parts) != 4:
        return svg_string

    try:
        vb_x, vb_y, vb_w, vb_h = [float(x) for x in vb_parts]
    except ValueError:
        return svg_string

    if vb_w <= 0 or vb_h <= 0:
        return svg_string

    # ── 1. Add padding to the viewBox ──────────────────────────
    # ezdxf computes the viewBox from exact geometry extents.
    # Entities on the boundary (e.g. a 3D cube projected top-down)
    # have their strokes half-clipped.  A 3% margin on each side
    # ensures full stroke visibility and a clean inset.
    pad_x = vb_w * 0.03
    pad_y = vb_h * 0.03
    new_vb_x = vb_x - pad_x
    new_vb_y = vb_y - pad_y
    new_vb_w = vb_w + 2 * pad_x
    new_vb_h = vb_h + 2 * pad_y

    # Use .2f (never scientific notation) — MuPDF's SVG parser
    # cannot handle exponent forms like "1.06e+06" in viewBox.
    svg_string = re.sub(
        r'viewBox="[^"]*"',
        f'viewBox="{new_vb_x:.2f} {new_vb_y:.2f} {new_vb_w:.2f} {new_vb_h:.2f}"',
        svg_string,
        count=1,
    )

    # ── 2. Set reasonable pixel dimensions (800px wide) ────────
    target_width = 800
    aspect = new_vb_h / new_vb_w
    target_height = max(200, min(int(target_width * aspect), 1200))

    # Replace width and height attributes on the root <svg> element
    svg_string = re.sub(
        r'(<svg\s[^>]*?)width="[^"]*"',
        f'\\1width="{target_width}"',
        svg_string,
        count=1,
    )
    svg_string = re.sub(
        r'(<svg\s[^>]*?)height="[^"]*"',
        f'\\1height="{target_height}"',
        svg_string,
        count=1,
    )

    # ── 3. Normalize stroke-width ──────────────────────────────
    # ~0.25% of the viewBox largest dimension produces clean thin
    # lines (~2px at 800px display width).  Use .6g formatting so
    # small-viewBox models keep enough precision instead of
    # rounding to "0.0" (which makes strokes invisible).
    ideal_stroke = max(max(new_vb_w, new_vb_h) * 0.0025, 1e-6)
    svg_string = re.sub(
        r'stroke-width:\s*[\d.eE+\-]+',
        f'stroke-width: {ideal_stroke:.6g}',
        svg_string,
    )

    return svg_string


def _detect_xrefs(doc, log_warn):
    """Detect external references and warn the user."""
    try:
        for block in doc.blocks:
            if block.is_xref:
                xref_path = block.dxf.xref_path if hasattr(block.dxf, "xref_path") else "unknown"
                log_warn(f"External reference (XREF) detected: {block.name} → {xref_path}")
    except Exception:
        pass
