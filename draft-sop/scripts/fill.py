"""
fill.py — copied from bixl-studio modules/sop/fill.py (keep in sync). Fill IXL SOP Word template with step images and text.

Entry point:
    fill_sop(steps, part_no, part_name, doc_no,
             format_key="a3-landscape", steps_per_page=8,
             template_path=None, output_path=None)

steps is a list of dicts: {"image": path|bytes, "text": str, "annotations": list|None}
  annotations entries are dicts with a "type" of "oval"|"rect"|"line"|"arrow"|"text"

Template selection:
  Picks from docx/sop/{format_key}__{steps_per_page}steps.docx.
  Pass template_path to override.

Template layout:
  Each page table repeats (heading / image / text) blocks.
  Grid (cols x n_blocks) is inferred from the table dimensions.
  Row pattern per block i: heading=i*3, image=i*3+1, text=i*3+2.

Multi-page:
  Steps beyond template capacity: deep-copy template table after page break,
  continue step numbering, blank headings for unfilled trailing slots.
"""
from __future__ import annotations

import copy
import io
import os
from typing import Optional, Union

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from PIL import Image as PILImage
from xml.sax.saxutils import escape as xml_escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(ROOT, "assets", "templates")

IMG_PADDING_CM = 0.18   # vertical breathing room inside image cell
BODY_FONT = "Century Gothic"
BODY_PT = 11
_PT_PER_CM = 72 / 2.54


# Template helpers

def _template_path(format_key: str, steps_per_page: int) -> str:
    return os.path.join(TEMPLATE_DIR, f"{format_key}__{steps_per_page}steps.docx")


def _infer_grid(table) -> tuple[int, int]:
    """Return (cols, n_blocks) from a fill-template table."""
    return len(table.columns), len(table.rows) // 3


def _col_width_cm(table, col: int) -> float:
    tc = table.rows[0].cells[col]._tc
    tcPr = tc.find(qn("w:tcPr"))
    if tcPr is not None:
        tcW = tcPr.find(qn("w:tcW"))
        if tcW is not None:
            return int(tcW.get(qn("w:w"))) / 1440 * 2.54
    return 12.0


def _image_row_height_cm(table, block: int) -> float:
    trPr = table.rows[block * 3 + 1]._tr.find(qn("w:trPr"))
    if trPr is not None:
        trH = trPr.find(qn("w:trHeight"))
        if trH is not None:
            return int(trH.get(qn("w:val"))) / 1440 * 2.54
    return 5.5


# Cell helpers

def _clear_cell(cell) -> None:
    for p in cell.paragraphs[1:]:
        p._element.getparent().remove(p._element)
    for run in list(cell.paragraphs[0].runs):
        run._element.getparent().remove(run._element)


_EMU_PER_PT = 12700   # 1pt = 12700 EMU
_TWIP_PER_PT = 20     # 1pt = 20 twips (dxa)


def _cell_content_width_pt(cell):
    """Inner (text-column) width of a cell in points, or None if unknown.

    The image is centred in this box via the paragraph's jc=center, so its left
    edge sits (content_width - image_width)/2 in from the column's left edge --
    the offset the VML shapes must add (see add_image_to_cell)."""
    w = cell.width  # EMU, or None if the cell carries no explicit width
    if not w:
        return None
    left = right = 115  # template default tcMar (twips) if not otherwise set
    tcPr = cell._tc.find(qn("w:tcPr"))
    if tcPr is not None:
        tcMar = tcPr.find(qn("w:tcMar"))
        if tcMar is not None:
            le = tcMar.find(qn("w:left"))
            re_ = tcMar.find(qn("w:right"))
            if le is not None and le.get(qn("w:w")) is not None:
                left = int(le.get(qn("w:w")))
            if re_ is not None and re_.get(qn("w:w")) is not None:
                right = int(re_.get(qn("w:w")))
    return w / _EMU_PER_PT - (left + right) / _TWIP_PER_PT


def _set_cell_vertical_align(cell, align: str = "center") -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    for existing in tcPr.findall(qn("w:vAlign")):
        tcPr.remove(existing)
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), align)
    tcPr.append(vAlign)


def _open_image(image: Union[str, bytes]) -> PILImage.Image:
    if isinstance(image, (bytes, bytearray)):
        return PILImage.open(io.BytesIO(image), formats=["JPEG", "PNG"])
    return PILImage.open(image, formats=["JPEG", "PNG"])


def _image_source(image: Union[str, bytes]):
    if isinstance(image, (bytes, bytearray)):
        return io.BytesIO(image)
    return image


def _safe_stroke(v) -> str:
    """Escape a client-supplied stroke color for a VML XML attribute."""
    return xml_escape(str(v if v is not None else "#ee0000"), {'"': "&quot;"})


def _safe_weight_pt(v) -> float:
    """Coerce a client-supplied stroke weight to a safe numeric value."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return 2.25


def _oval_run_xml(ovals: list, img_w_pt: float, img_h_pt: float,
                  x_off_pt: float = 0.0, hrel: str = "char") -> str:
    """Build one w:r holding one w:pict/v:oval per annotation, sized against the
    displayed image box (img_w_pt x img_h_pt). Coordinates/sizes are fractions
    (0..1) of that box. python-docx has no v:/o: prefixes in its nsmap, so this
    is assembled as a raw XML string and parsed with parse_xml.

    x_off_pt/hrel: horizontal centring offset + anchor origin (see
    add_image_to_cell) -- the image is centred in the cell, so shapes anchor to
    the cell's text column and add x_off_pt rather than trusting char-relative
    anchoring over a centred image, which Word drifts."""
    picts = []
    for oval in ovals:
        x = float(oval.get("x", 0))
        y = float(oval.get("y", 0))
        w = float(oval.get("w", 0))
        h = float(oval.get("h", 0))
        stroke = _safe_stroke(oval.get("stroke"))
        weight_pt = _safe_weight_pt(oval.get("weight_pt", 2.25))
        filled = "t" if oval.get("filled") else "f"
        margin_left = round(x_off_pt + x * img_w_pt, 2)
        margin_top = round(y * img_h_pt, 2)
        width = round(w * img_w_pt, 2)
        height = round(h * img_h_pt, 2)
        style = (
            f"position:absolute;mso-position-horizontal-relative:{hrel};"
            f"mso-position-vertical-relative:line;margin-left:{margin_left}pt;"
            f"margin-top:{margin_top}pt;width:{width}pt;height:{height}pt;z-index:2"
        )
        picts.append(
            f'<w:pict><v:oval o:allowincell="t" filled="{filled}" stroked="t" '
            f'strokecolor="{stroke}" strokeweight="{weight_pt}pt" style="{style}"/></w:pict>'
        )
    return (
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:o="urn:schemas-microsoft-com:office:office">'
        + "".join(picts) +
        "</w:r>"
    )


def _rect_run_xml(rects: list, img_w_pt: float, img_h_pt: float,
                  x_off_pt: float = 0.0, hrel: str = "char") -> str:
    """Same as _oval_run_xml but v:rect (square corners)."""
    picts = []
    for rect in rects:
        x = float(rect.get("x", 0))
        y = float(rect.get("y", 0))
        w = float(rect.get("w", 0))
        h = float(rect.get("h", 0))
        stroke = _safe_stroke(rect.get("stroke"))
        weight_pt = _safe_weight_pt(rect.get("weight_pt", 2.25))
        filled = "t" if rect.get("filled") else "f"
        margin_left = round(x_off_pt + x * img_w_pt, 2)
        margin_top = round(y * img_h_pt, 2)
        width = round(w * img_w_pt, 2)
        height = round(h * img_h_pt, 2)
        style = (
            f"position:absolute;mso-position-horizontal-relative:{hrel};"
            f"mso-position-vertical-relative:line;margin-left:{margin_left}pt;"
            f"margin-top:{margin_top}pt;width:{width}pt;height:{height}pt;z-index:2"
        )
        picts.append(
            f'<w:pict><v:rect o:allowincell="t" filled="{filled}" stroked="t" '
            f'strokecolor="{stroke}" strokeweight="{weight_pt}pt" style="{style}"/></w:pict>'
        )
    return (
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:o="urn:schemas-microsoft-com:office:office">'
        + "".join(picts) +
        "</w:r>"
    )


def _line_run_xml(lines: list, img_w_pt: float, img_h_pt: float,
                  x_off_pt: float = 0.0, hrel: str = "char") -> str:
    """Build one w:r holding one w:pict/v:line per annotation. Handles both
    "line" and "arrow" -- arrow adds a nested <v:stroke endarrow="block"/>."""
    picts = []
    for line in lines:
        x1 = float(line.get("x1", 0))
        y1 = float(line.get("y1", 0))
        x2 = float(line.get("x2", 0))
        y2 = float(line.get("y2", 0))
        stroke = _safe_stroke(line.get("stroke"))
        weight_pt = _safe_weight_pt(line.get("weight_pt", 2.25))
        from_pt = f"{round(x_off_pt + x1 * img_w_pt, 2)}pt,{round(y1 * img_h_pt, 2)}pt"
        to_pt = f"{round(x_off_pt + x2 * img_w_pt, 2)}pt,{round(y2 * img_h_pt, 2)}pt"
        style = (
            f"position:absolute;mso-position-horizontal-relative:{hrel};"
            "mso-position-vertical-relative:line;z-index:2"
        )
        stroke_child = '<v:stroke endarrow="block"/>' if line.get("type") == "arrow" else ""
        picts.append(
            f'<w:pict><v:line o:allowincell="t" from="{from_pt}" to="{to_pt}" '
            f'strokecolor="{stroke}" strokeweight="{weight_pt}pt" style="{style}">'
            f'{stroke_child}</v:line></w:pict>'
        )
    return (
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:o="urn:schemas-microsoft-com:office:office">'
        + "".join(picts) +
        "</w:r>"
    )


def _text_run_xml(texts: list, img_w_pt: float, img_h_pt: float,
                  x_off_pt: float = 0.0, hrel: str = "char") -> str:
    """Build one w:r holding one w:pict/v:rect (white fill) with a v:textbox
    label per annotation. First place in this codebase writing arbitrary user
    text into raw XML -- must escape it."""
    picts = []
    for t in texts:
        x = float(t.get("x", 0))
        y = float(t.get("y", 0))
        w = float(t.get("w", 0))
        h = float(t.get("h", 0))
        stroke = _safe_stroke(t.get("stroke"))
        weight_pt = _safe_weight_pt(t.get("weight_pt", 2.25))
        label = xml_escape(str(t.get("text") or ""))
        margin_left = round(x_off_pt + x * img_w_pt, 2)
        margin_top = round(y * img_h_pt, 2)
        width = round(w * img_w_pt, 2)
        height = round(h * img_h_pt, 2)
        style = (
            f"position:absolute;mso-position-horizontal-relative:{hrel};"
            f"mso-position-vertical-relative:line;margin-left:{margin_left}pt;"
            f"margin-top:{margin_top}pt;width:{width}pt;height:{height}pt;z-index:2;"
            f"v-text-anchor:middle"
        )
        picts.append(
            f'<w:pict><v:rect o:allowincell="t" filled="t" fillcolor="#ffffff" stroked="t" '
            f'strokecolor="{stroke}" strokeweight="{weight_pt}pt" style="{style}">'
            f'<v:textbox inset="1pt,1pt,1pt,1pt"><w:txbxContent>'
            f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="{BODY_FONT}" w:hAnsi="{BODY_FONT}"/>'
            f'<w:sz w:val="24"/><w:color w:val="1A1A1A"/></w:rPr>'
            f'<w:t xml:space="preserve">{label}</w:t></w:r></w:p>'
            f'</w:txbxContent></v:textbox></v:rect></w:pict>'
        )
    return (
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:o="urn:schemas-microsoft-com:office:office">'
        + "".join(picts) +
        "</w:r>"
    )


def add_image_to_cell(cell, image: Union[str, bytes],
                      max_width_cm: float = 12.0,
                      max_height_cm: float = 5.5,
                      annotations=None) -> None:
    """Insert image scaled to fit cell, horizontally + vertically centred."""
    img = _open_image(image)
    w, h = img.size
    scale = min(max_width_cm / w, max_height_cm / h)
    final_width_cm = w * scale
    final_height_cm = h * scale

    _clear_cell(cell)
    _set_cell_vertical_align(cell, "center")
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()
    run.add_picture(_image_source(image), width=Cm(final_width_cm))

    by_type: dict = {}
    for a in (annotations or []):
        if isinstance(a, dict) and a.get("type") in ("oval", "rect", "line", "arrow", "text"):
            by_type.setdefault(a["type"], []).append(a)

    img_w_pt = final_width_cm * _PT_PER_CM
    img_h_pt = final_height_cm * _PT_PER_CM

    # Horizontal anchor: the image is centred in the cell (para jc=center), but
    # floating VML shapes don't participate in that centring -- Word anchors
    # them char-relative at the *un*-centred line start, so they drift left by
    # the centring gap (can be ~2cm for a narrow portrait photo in a wide cell).
    # Fix: anchor to the cell's text column (a fixed reference Word places
    # deterministically) and add the centring offset ourselves. Vertical is
    # unaffected -- vAlign=center moves the whole line block, shapes included,
    # so line-relative y already tracks the image. Fall back to char-relative
    # (no offset -- old behaviour) if the cell width is unknown.
    content_w_pt = _cell_content_width_pt(cell)
    if content_w_pt:
        x_off_pt = max(0.0, (content_w_pt - img_w_pt) / 2)
        hrel = "column"
    else:
        x_off_pt, hrel = 0.0, "char"

    # Insert each pict run immediately before the picture run in the same
    # paragraph. Order among shape-type runs doesn't matter -- each
    # independently anchors to the same origin per-run.
    if by_type.get("oval"):
        run._r.addprevious(parse_xml(_oval_run_xml(by_type["oval"], img_w_pt, img_h_pt, x_off_pt, hrel)))
    if by_type.get("rect"):
        run._r.addprevious(parse_xml(_rect_run_xml(by_type["rect"], img_w_pt, img_h_pt, x_off_pt, hrel)))
    lines = by_type.get("line", []) + by_type.get("arrow", [])
    if lines:
        run._r.addprevious(parse_xml(_line_run_xml(lines, img_w_pt, img_h_pt, x_off_pt, hrel)))
    if by_type.get("text"):
        run._r.addprevious(parse_xml(_text_run_xml(by_type["text"], img_w_pt, img_h_pt, x_off_pt, hrel)))


def add_text_to_cell(cell, text: str) -> None:
    _clear_cell(cell)
    para = cell.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = para.add_run(text or "")
    run.font.name = BODY_FONT
    run.font.size = Pt(BODY_PT)


def set_heading_text(cell, text: str) -> None:
    """Set or blank STEP N heading run, preserving existing formatting."""
    para = cell.paragraphs[0]
    if para.runs:
        first = para.runs[0]
        first.text = text
        for extra in list(para.runs[1:]):
            extra._element.getparent().remove(extra._element)
    elif text:
        run = para.add_run(text)
        run.font.name = BODY_FONT


# Header / footer field replacement (handles split runs)

def _replace_paragraph_text(para, new_text: str) -> None:
    if not para.runs:
        para.add_run(new_text)
        return
    first = para.runs[0]
    rPr = first._r.find(qn("w:rPr"))
    for run in list(para.runs):
        run._element.getparent().remove(run._element)
    new_r = OxmlElement("w:r")
    if rPr is not None:
        new_r.append(copy.deepcopy(rPr))
    new_t = OxmlElement("w:t")
    new_t.set(qn("xml:space"), "preserve")
    new_t.text = new_text
    new_r.append(new_t)
    para._p.append(new_r)


def set_part_title(doc, part_no: str, part_name: str) -> None:
    """Header table row 1 cell 2: '<part_no> - <part_name>'."""
    header = doc.sections[0].header
    if not header.tables:
        return
    para = header.tables[0].rows[1].cells[-1].paragraphs[0]  # [2] landscape, [1] portrait
    title = f"{part_no} - {part_name}" if part_no else part_name
    _replace_paragraph_text(para, title)


def set_doc_number(doc, doc_no: str) -> None:
    """Footer table row 0 cell 0: '<doc_no>'."""
    footer = doc.sections[0].footer
    if not footer.tables:
        return
    para = footer.tables[0].rows[0].cells[0].paragraphs[0]
    _replace_paragraph_text(para, doc_no)


# Page table fill

def _fill_page_table(table, page_steps: list, base_index: int) -> None:
    """Fill one template table. Blank heading for any unfilled trailing slot."""
    cols, n_blocks = _infer_grid(table)
    steps_per_page = cols * n_blocks

    for slot in range(steps_per_page):
        block = slot // cols
        col = slot % cols
        step_no = base_index + slot + 1

        heading_cell = table.rows[block * 3].cells[col]
        image_cell = table.rows[block * 3 + 1].cells[col]
        text_cell = table.rows[block * 3 + 2].cells[col]

        step = page_steps[slot] if slot < len(page_steps) else None
        has_content = bool(step and (step.get("image") or step.get("text")))

        if has_content:
            set_heading_text(heading_cell, f"STEP {step_no}")
            if step.get("image"):
                cw = _col_width_cm(table, col) - 0.2
                rh = _image_row_height_cm(table, block) - IMG_PADDING_CM * 2
                add_image_to_cell(image_cell, step["image"],
                                  max_width_cm=cw, max_height_cm=rh,
                                  annotations=step.get("annotations"))
            else:
                _clear_cell(image_cell)
            # Always write text (even empty) so template sample text never leaks through.
            add_text_to_cell(text_cell, step.get("text") or "")
        else:
            # Empty step: clear heading, image, and text so copied content doesn't bleed through.

            set_heading_text(heading_cell, "")
            _clear_cell(image_cell)
            _clear_cell(text_cell)


def _append_page_break_and_table(doc, source_table):
    """Deep-copy source_table into body before sectPr, force it onto a new page."""
    body = doc.element.body
    children = list(body)
    sectPr = body.find(qn("w:sectPr"))
    insert_idx = children.index(sectPr) if sectPr is not None else len(children)

    new_tbl = copy.deepcopy(source_table._tbl)
    body.insert(insert_idx, new_tbl)
    from docx.table import Table
    table = Table(new_tbl, doc)

    # Force page break before this table via the first heading cell's paragraph.
    # A separate break paragraph can strand on the last page and push the table
    # one page further than expected.
    first_para = table.rows[0].cells[0].paragraphs[0]
    pPr = first_para._p.get_or_add_pPr()
    for old in pPr.findall(qn("w:pageBreakBefore")):
        pPr.remove(old)
    pPr.append(OxmlElement("w:pageBreakBefore"))
    return table


# Public entry point

def fill_sop(steps,
             part_no: str,
             part_name: str,
             doc_no: str,
             format_key: str = "a3-landscape",
             steps_per_page: int = 8,
             template_path: Optional[str] = None,
             output_path: Optional[str] = None) -> Union[str, bytes]:
    """Fill the SOP template and return bytes or save to output_path.

    Args:
        steps: list of {"image": path|bytes, "text": str, "annotations": list|None}, any length.
        part_no, part_name, doc_no: header/footer values.
        format_key: "a3-landscape", "a3-portrait", "a4-landscape", "a4-portrait".
        steps_per_page: 1, 2, 4, 6, or 8 (must match an available template).
        template_path: override auto-selected template.
        output_path: save location; if None returns bytes.
    """
    if template_path is None:
        template_path = _template_path(format_key, steps_per_page)

    doc = Document(template_path)
    # Portrait templates open with a 1x1 PPE table; the step grid is the first
    # table with heading/image/text rows (doc.tables[0] gave 0 steps/page and looped).
    first_table = next(t for t in doc.tables if len(t.rows) >= 3)
    cols, n_blocks = _infer_grid(first_table)
    spp = cols * n_blocks

    _fill_page_table(first_table, steps[:spp], base_index=0)

    page = 1
    while page * spp < len(steps):
        start = page * spp
        page_steps = steps[start:start + spp]
        new_table = _append_page_break_and_table(doc, first_table)
        _fill_page_table(new_table, page_steps, base_index=start)
        page += 1

    set_part_title(doc, part_no, part_name)
    set_doc_number(doc, doc_no)

    if output_path:
        doc.save(output_path)
        return output_path

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


if __name__ == "__main__":
    import tempfile
    from PIL import Image, ImageDraw

    tmp = tempfile.mkdtemp()
    demo_steps = []
    for i in range(6):
        p = os.path.join(tmp, f"s{i}.jpg")
        im = Image.new("RGB", (400, 300), (60 + i * 25, 90, 120))
        ImageDraw.Draw(im).text((180, 140), f"Step {i + 1}", fill="white")
        im.save(p)
        demo_steps.append({"image": p, "text": f"Description for step {i + 1}."})

    out = os.path.join(tmp, "demo_output.docx")
    fill_sop(demo_steps, "36611", "Tastic Luminate Heat Module", "A0866",
             format_key="a3-landscape", steps_per_page=8, output_path=out)
    print("Wrote", out)
