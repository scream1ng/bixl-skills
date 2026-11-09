"""Draft SOP: dress photos, review HTML with comment pins, approve, export IXL Word SOP.

    python scripts/sop.py prep    JOB/spec.json   # dressed/<key>.jpg + <key>.grid.jpg
    python scripts/sop.py preview JOB/spec.json   # preview-rN.html
    python scripts/sop.py approve JOB/spec.json --note 'user wording'
    python scripts/sop.py export  JOB/spec.json [--render]
"""
import argparse
import base64
import hashlib
import html
import io
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RED = '#CC0000'
WEIGHT = 2.25
FORMATS = {'a3-landscape': (1, 2, 4, 8), 'a3-portrait': (1, 2, 4, 6),
           'a4-landscape': (1, 2), 'a4-portrait': (1, 2)}
COLS = {('a3-landscape', 1): 1, ('a3-landscape', 2): 2, ('a3-landscape', 4): 2, ('a3-landscape', 8): 4,
        ('a3-portrait', 1): 1, ('a3-portrait', 2): 1, ('a3-portrait', 4): 2, ('a3-portrait', 6): 2,
        ('a4-landscape', 1): 1, ('a4-landscape', 2): 2, ('a4-portrait', 1): 1, ('a4-portrait', 2): 1}
CIRCLED = '①②③④⑤⑥⑦⑧⑨'
MAX_WORDS = 10
MAX_CALLOUTS = 4
MAX_BULLETS = 4
MAX_SUBS = 8
TEXT_PT = 14
CALLOUT_CM = 0.9
MARK_TYPES = ('oval', 'rect', 'arrow', 'line', 'text')
KEY = re.compile(r'^[a-z0-9][a-z0-9-]*$')
LONG_EDGE = 1600
PREVIEW_EDGE = 720


def fail(msg):
    raise ValueError(msg)


def frac(v, name):
    if not isinstance(v, (int, float)) or not 0 <= v <= 1:
        fail(f'{name} must be a fraction 0..1')
    return float(v)


# ---------- spec ----------

def load(path):
    path = Path(path).resolve()
    spec = json.loads(path.read_text(encoding='utf-8'))
    if spec.get('version') != 1:
        fail('Expected version 1.')
    if not isinstance(spec.get('revision'), int) or spec['revision'] < 1:
        fail('Revision must be a positive integer.')
    part = spec.get('part') or {}
    for k in ('number', 'name', 'doc_no'):
        if not str(part.get(k, '')).strip():
            fail(f'part.{k} is required (ask the user; use "TBC" only if they say so).')
    steps = spec.get('steps') or []
    if not steps:
        fail('At least one step is required.')
    fmt = spec.setdefault('format', 'a3-landscape')
    if fmt not in FORMATS:
        fail(f'format must be one of {", ".join(FORMATS)}.')
    spp = spec.get('steps_per_page')
    if spp is None:
        spp = next((n for n in FORMATS[fmt] if n >= len(steps)), FORMATS[fmt][-1])
    if spp not in FORMATS[fmt]:
        fail(f'{fmt} supports {FORMATS[fmt]} steps per page.')
    spec['steps_per_page'] = spp
    keys = set()
    for i, s in enumerate(steps, 1):
        key = s.get('key', '')
        if not KEY.match(key) or key in keys:
            fail(f'Step {i}: key must be unique lowercase-kebab.')
        keys.add(key)
        if not (path.parent / s.get('photo', '')).is_file():
            fail(f'Step {key}: photo not found ({s.get("photo")}).')
        check_text(s)
        check_dress(s)
        for m in s.get('marks', []):
            check_mark(m, key)
    return path, spec


def words(text):
    return [w for w in re.split(r'\s+', text.strip()) if w and not all(c in CIRCLED for c in w)]


def bullets(text):
    """Step text -> [(level, line)]. A string is one bullet; a nested list holds
    sub-bullets of the bullet before it: ["Pack in carton", ["611061", "611060"]]."""
    if isinstance(text, str):
        text = [text]
    out = []
    for item in text if isinstance(text, list) else []:
        if isinstance(item, list) and out and out[-1][0] == 0:
            out += [(1, str(sub)) for sub in item]
        elif isinstance(item, str):
            out.append((0, item))
        else:
            return []
    return [(lvl, line.strip()) for lvl, line in out]


def check_text(step):
    key = step['key']
    lines = bullets(step.get('text'))
    if not lines or any(not line or '\n' in line for _, line in lines):
        fail(f'Step {key}: text is a bullet string or list of bullets (nested list = sub-bullets).')
    if sum(1 for lvl, _ in lines if lvl == 0) > MAX_BULLETS or sum(1 for lvl, _ in lines if lvl) > MAX_SUBS:
        fail(f'Step {key}: max {MAX_BULLETS} bullets and {MAX_SUBS} sub-bullets.')
    for lvl, line in lines:
        if len(words(line)) > MAX_WORDS:
            fail(f'Step {key}: "{line}" has {len(words(line))} words; max {MAX_WORDS} per bullet.')
    text = ' '.join(line for _, line in lines)
    callouts = step.get('callouts', [])
    if len(callouts) > MAX_CALLOUTS:
        fail(f'Step {key}: max {MAX_CALLOUTS} callouts per photo.')
    seen = set()
    for c in callouts:
        n = c.get('n')
        if not isinstance(n, int) or not 1 <= n <= 9 or n in seen:
            fail(f'Step {key}: callout n must be unique 1..9.')
        seen.add(n)
        for p in ('at', 'tag'):
            pt = c.get(p)
            if not (isinstance(pt, list) and len(pt) == 2):
                fail(f'Step {key}: callout {n} needs {p}: [x, y].')
            [frac(v, f'Step {key} callout {n} {p}') for v in pt]
    for ch in text:
        if ch in CIRCLED and CIRCLED.index(ch) + 1 not in seen:
            fail(f'Step {key}: text references {ch} but no callout {CIRCLED.index(ch) + 1}.')


def check_dress(step):
    d = step.get('dress', {})
    crop = d.get('crop')
    if crop is not None:
        if not (isinstance(crop, list) and len(crop) == 4):
            fail(f'Step {step["key"]}: dress.crop is [x0, y0, x1, y1] fractions.')
        x0, y0, x1, y1 = [frac(v, f'Step {step["key"]} crop') for v in crop]
        if x1 - x0 < 0.1 or y1 - y0 < 0.1:
            fail(f'Step {step["key"]}: crop too small.')
    if not isinstance(d.get('rotate', 0), (int, float)) or abs(d.get('rotate', 0)) > 45:
        fail(f'Step {step["key"]}: dress.rotate is degrees within ±45 (use turn for 90s).')
    if d.get('turn', 0) not in (0, 90, 180, 270):
        fail(f'Step {step["key"]}: dress.turn is 0/90/180/270.')


def check_mark(m, key):
    t = m.get('type')
    if t not in MARK_TYPES:
        fail(f'Step {key}: mark type must be one of {MARK_TYPES}.')
    names = ('x1', 'y1', 'x2', 'y2') if t in ('arrow', 'line') else ('x', 'y', 'w', 'h')
    for n in names:
        frac(m.get(n), f'Step {key} {t}.{n}')
    if t == 'text' and not str(m.get('text', '')).strip():
        fail(f'Step {key}: text mark needs text.')
    if t == 'text' and len(str(m['text']).split()) > 3:
        fail(f'Step {key}: photo labels are 1-3 words.')
    if 'to' in m:
        if t != 'text' or not (isinstance(m['to'], list) and len(m['to']) == 2):
            fail(f'Step {key}: "to": [x, y] is only for text labels.')
        [frac(v, f'Step {key} {m["text"]} to') for v in m['to']]


# ---------- photos ----------

def dressed_path(job, step):
    return job / 'dressed' / f'{step["key"]}.jpg'


def dress(job, step):
    from PIL import Image, ImageOps, ImageFilter, ImageStat
    d = step.get('dress', {})
    im = ImageOps.exif_transpose(Image.open(job / step['photo'])).convert('RGB')
    if d.get('turn'):
        im = im.rotate(-d['turn'], expand=True)
    if d.get('rotate'):
        im = im.rotate(-d['rotate'], resample=Image.BICUBIC, expand=True, fillcolor='white')
    if d.get('crop'):
        x0, y0, x1, y1 = d['crop']
        W, H = im.size
        im = im.crop((round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H)))
    if d.get('light', True):
        means = ImageStat.Stat(im).mean
        grey = sum(means) / 3
        gains = [max(0.85, min(1.2, grey / m)) if m else 1 for m in means]
        im = Image.merge('RGB', [ch.point(lambda v, g=g: min(255, round(v * g))) for ch, g in zip(im.split(), gains)])
        im = Image.blend(im, ImageOps.autocontrast(im, cutoff=1, preserve_tone=True), 0.5)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    im.thumbnail((LONG_EDGE, LONG_EDGE), Image.LANCZOS)
    return im


def grid(im):
    from PIL import ImageDraw
    g = im.copy()
    draw = ImageDraw.Draw(g)
    W, H = g.size
    for i in range(1, 10):
        x, y = W * i / 10, H * i / 10
        draw.line([(x, 0), (x, H)], fill=(255, 230, 0), width=1)
        draw.line([(0, y), (W, y)], fill=(255, 230, 0), width=1)
        draw.text((x + 3, 3), f'.{i}', fill=(255, 0, 0))
        draw.text((3, y + 3), f'.{i}', fill=(255, 0, 0))
    return g


def prep(path):
    path, spec = load(path)
    out = []
    (path.parent / 'dressed').mkdir(exist_ok=True)
    for s in spec['steps']:
        im = dress(path.parent, s)
        target = dressed_path(path.parent, s)
        im.save(target, 'JPEG', quality=88)
        grid(im).save(target.with_suffix('.grid.jpg'), 'JPEG', quality=80)
        out.append(f'{target.name} {im.size[0]}x{im.size[1]}')
    return '\n'.join(out)


# ---------- annotations ----------

_CELL = {}


def cell_cm(spec):
    """(width, height) cm of the photo box in the chosen template, as fill.py sizes it."""
    key = (spec['format'], spec['steps_per_page'])
    if key not in _CELL:
        sys.path.insert(0, str(ROOT / 'scripts'))
        import fill
        from docx import Document
        doc = Document(fill._template_path(*key))
        t = next(t for t in doc.tables if len(t.rows) >= 3)
        _CELL[key] = (fill._col_width_cm(t, 0) - 0.2, fill._image_row_height_cm(t, 0) - fill.IMG_PADDING_CM * 2)
    return _CELL[key]


def leader(box, to):
    """Arrow from the edge of box (x, y, w, h) to point to; None if to is inside the box."""
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    dx, dy = to[0] - cx, to[1] - cy
    t = min(w / 2 / abs(dx) if dx else 1, h / 2 / abs(dy) if dy else 1)
    if t >= 1:
        return None
    return {'type': 'arrow', 'x1': cx + dx * t, 'y1': cy + dy * t, 'x2': to[0], 'y2': to[1],
            'stroke': RED, 'weight_pt': WEIGHT}


def targets(step):
    """(name, point) for every arrowhead, for the zoomed check sheet."""
    out = []
    for m in step.get('marks', []):
        if m['type'] == 'text' and 'to' in m:
            out.append((m['text'], m['to']))
        elif m['type'] == 'arrow':
            out.append((m.get('target', 'arrow'), [m['x2'], m['y2']]))
    out += [(f'callout {c["n"]}', c['at']) for c in step.get('callouts', [])]
    return out


def compile_marks(step, size, cell=(12.0, 5.5)):
    """Spec marks + callouts -> fill.py annotation dicts (fractions of the dressed photo)."""
    W, H = size
    scale = min(cell[0] / W, cell[1] / H)  # cm per pixel on paper
    out = []
    for m in step.get('marks', []):
        a = {k: v for k, v in m.items() if k not in ('color', 'to', 'target')}
        a.update(stroke=m.get('color', RED), weight_pt=WEIGHT)
        if a['type'] in ('oval', 'rect'):
            a['filled'] = False
        if 'to' in m:
            arrow = leader((m['x'], m['y'], m['w'], m['h']), m['to'])
            if arrow:
                out.append(arrow)
        out.append(a)
    side = CALLOUT_CM / scale  # same size on paper whatever the layout
    bw, bh = min(side / W, 0.3), min(side / H, 0.3)
    for c in step.get('callouts', []):
        (ax, ay), (tx, ty) = c['at'], c['tag']
        x = min(max(tx - bw / 2, 0), 1 - bw)
        y = min(max(ty - bh / 2, 0), 1 - bh)
        arrow = leader((x, y, bw, bh), (ax, ay))
        if arrow:
            out.append(arrow)
        out.append({'type': 'text', 'x': x, 'y': y, 'w': bw, 'h': bh, 'text': str(c['n']),
                    'stroke': RED, 'weight_pt': WEIGHT})
    return out


def svg_overlay(marks, W, H):
    esc = lambda v: html.escape(str(v), quote=True)
    sw = max(W, H) / 220
    parts = [f'<svg class="marks" viewBox="0 0 {W} {H}" preserveAspectRatio="none">'
             f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4" markerHeight="4" orient="auto">'
             f'<path d="M0,0L10,5L0,10z" fill="{RED}"/></marker></defs>']
    for m in marks:
        c = esc(m['stroke'])
        if m['type'] in ('arrow', 'line'):
            head = ' marker-end="url(#ah)"' if m['type'] == 'arrow' else ''
            parts.append(f'<line x1="{m["x1"]*W:.1f}" y1="{m["y1"]*H:.1f}" x2="{m["x2"]*W:.1f}" y2="{m["y2"]*H:.1f}" stroke="{c}" stroke-width="{sw:.1f}"{head}/>')
        elif m['type'] == 'oval':
            parts.append(f'<ellipse cx="{(m["x"]+m["w"]/2)*W:.1f}" cy="{(m["y"]+m["h"]/2)*H:.1f}" rx="{m["w"]*W/2:.1f}" ry="{m["h"]*H/2:.1f}" fill="none" stroke="{c}" stroke-width="{sw:.1f}"/>')
        elif m['type'] == 'rect':
            parts.append(f'<rect x="{m["x"]*W:.1f}" y="{m["y"]*H:.1f}" width="{m["w"]*W:.1f}" height="{m["h"]*H:.1f}" fill="none" stroke="{c}" stroke-width="{sw:.1f}"/>')
    for m in marks:  # labels on top, like Word z-index 2
        if m['type'] == 'text':
            x, y, w, h = m['x'] * W, m['y'] * H, m['w'] * W, m['h'] * H
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#fff" stroke="{esc(m["stroke"])}" stroke-width="{sw:.1f}"/>'
                         f'<text x="{x+w/2:.1f}" y="{y+h/2:.1f}" font-size="{h*0.6:.1f}" text-anchor="middle" dominant-baseline="central">{esc(m["text"])}</text>')
    parts.append('</svg>')
    return ''.join(parts)


# ---------- review ----------

def fingerprint(path, spec):
    h = hashlib.sha256(path.read_bytes())
    for s in spec['steps']:
        p = dressed_path(path.parent, s)
        if not p.is_file():
            fail(f'Run prep first: {p.name} missing.')
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def data_uri(im, edge=PREVIEW_EDGE, quality=72):
    im = im.copy()
    im.thumbnail((edge, edge))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=quality)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def check_sheet(job, spec):
    """Zoomed crop around every arrowhead with a crosshair, captioned with what it must hit."""
    from PIL import Image, ImageDraw
    tiles = []
    for i, s in enumerate(spec['steps'], 1):
        im = Image.open(dressed_path(job, s))
        W, H = im.size
        r = round(0.12 * max(W, H))
        for name, (x, y) in targets(s):
            px, py = round(x * W), round(y * H)
            tile = Image.new('RGB', (2 * r, 2 * r), 'white')
            tile.paste(im.crop((px - r, py - r, px + r, py + r)), (0, 0))
            tile = tile.resize((300, 300))
            d = ImageDraw.Draw(tile)
            d.line([(150, 120), (150, 180)], fill=(255, 0, 255), width=2)
            d.line([(120, 150), (180, 150)], fill=(255, 0, 255), width=2)
            d.rectangle([0, 278, 300, 300], fill='black')
            d.text((5, 283), f'Step {i}: {name}', fill='white')
            tiles.append(tile)
    if not tiles:
        return None
    cols = 4
    sheet = Image.new('RGB', (cols * 304, math.ceil(len(tiles) / cols) * 304), 'grey')
    for n, t in enumerate(tiles):
        sheet.paste(t, ((n % cols) * 304, (n // cols) * 304))
    out = job / f'check-r{spec["revision"]}.jpg'
    sheet.save(out, quality=85)
    return out


def logo_uri():
    from zipfile import ZipFile
    from PIL import Image
    with ZipFile(ROOT / 'assets' / 'templates' / 'a3-landscape__8steps.docx') as z:
        im = Image.open(io.BytesIO(z.read('word/media/image9.jpg'))).convert('RGB')
    return data_uri(im, 260, 80)


def preview(path):
    from PIL import Image
    path, spec = load(path)
    stamp = fingerprint(path, spec)
    esc = lambda v: html.escape(str(v), quote=True)
    spp, fmt = spec['steps_per_page'], spec['format']
    cols = COLS[(fmt, spp)]
    pages = math.ceil(len(spec['steps']) / spp)
    sheets = []
    for p in range(pages):
        cells = []
        for i, s in enumerate(spec['steps'][p * spp:(p + 1) * spp], p * spp + 1):
            im = Image.open(dressed_path(path.parent, s))
            W, H = im.size
            cells.append(
                f'<div class="step" data-step="{esc(s["key"])}"><div class="head">STEP {i}</div>'
                f'<div class="frame"><div class="photo"><img src="{data_uri(im)}" alt="">'
                f'{svg_overlay(compile_marks(s, (W, H), cell_cm(spec)), W, H)}</div></div>'
                f'<div class="text" tabindex="0">{bullets_html(s["text"], esc)}</div></div>')
        sheets.append(f'<div class="page" style="grid-template-columns:repeat({cols},1fr)">{"".join(cells)}</div>')
    meta = {'part': spec['part']['number'], 'name': spec['part']['name'], 'revision': spec['revision'],
            'fingerprint': stamp, 'steps': {s['key']: i for i, s in enumerate(spec['steps'], 1)}}
    tokens = {
        'TITLE': esc(f'{spec["part"]["number"]} - {spec["part"]["name"]}'),
        'DOC': esc(spec['part']['doc_no']), 'REVISION': str(spec['revision']),
        'FORMAT': esc(f'{fmt} · {spp}/page · {len(spec["steps"])} steps'),
        'LOGO': logo_uri(), 'PAGES': ''.join(sheets),
        'CONFIRM_ITEMS': ''.join('<li>' + esc(t) + '</li>' for t in spec.get('to_confirm', [])[:3]),
        'CONFIRM_HIDDEN': '' if spec.get('to_confirm') else 'hidden',
        'META': json.dumps(meta).replace('<', '\\u003c'),
        'COMMENTS_SCRIPT': (ROOT / 'scripts' / 'comments.js').read_text(encoding='utf-8'),
    }
    content = (ROOT / 'scripts' / 'preview.html').read_text(encoding='utf-8')
    for k, v in tokens.items():
        content = content.replace('{{' + k + '}}', v)
    out = path.parent / f'preview-r{spec["revision"]}.html'
    if out.exists() and out.read_text(encoding='utf-8') != content:
        fail('This revision already exists with different content; increment revision.')
    out.write_text(content, encoding='utf-8')
    sheet = check_sheet(path.parent, spec)
    return f'{out}\ncheck arrowheads: {sheet}' if sheet else out


def snapshot(path):
    path, spec = load(path)
    stamp = fingerprint(path, spec)
    page = path.parent / f'preview-r{spec["revision"]}.html'
    if not page.is_file() or stamp not in page.read_text(encoding='utf-8'):
        fail('Preview is missing or stale; increment revision and regenerate.')
    return {'revision': spec['revision'], 'fingerprint': stamp,
            'html_sha256': hashlib.sha256(page.read_bytes()).hexdigest()}


def approve(path, note):
    if not note.strip():
        fail('Record the actual approval wording.')
    target = Path(path).resolve().parent / 'approval.json'
    target.write_text(json.dumps({**snapshot(path), 'user_note': note}, indent=2), encoding='utf-8')
    return target


# ---------- export ----------

def export(path, render=False):
    from PIL import Image
    path, spec = load(path)
    rec = path.parent / 'approval.json'
    if not rec.is_file():
        fail('No approval. Review the HTML preview first.')
    if any(json.loads(rec.read_text(encoding='utf-8')).get(k) != v for k, v in snapshot(path).items()):
        fail('Approval is stale; review the current revision.')
    sys.path.insert(0, str(ROOT / 'scripts'))
    from fill import fill_sop
    steps = []
    for s in spec['steps']:
        p = dressed_path(path.parent, s)
        steps.append({'image': p.read_bytes(), 'text': ' ',
                      'annotations': compile_marks(s, Image.open(p).size, cell_cm(spec))})
    part = spec['part']
    name = f'{part["doc_no"]} - {part["number"]} {part["name"]}'
    name = re.sub(r'\s+', ' ', re.sub(r'[\\/:*?"<>|]', ' ', name)).strip()
    out = path.parent / f'{name}.docx'
    fill_sop(steps, part['number'], part.get('title') or part['name'], part['doc_no'],
             format_key=spec['format'], steps_per_page=spec['steps_per_page'], output_path=str(out))
    write_bullets(out, spec)
    report = verify(out, spec)
    if render:
        report += '\n' + render_pages(out, math.ceil(len(steps) / spec['steps_per_page']))
    return f'{out}\n{report}'


def bullets_html(text, esc):
    return ''.join(f'<div class="b{lvl}"><span>{"-" if lvl == 0 else "o"}</span>{esc(line)}</div>'
                   for lvl, line in bullets(text))


LIST_XML = (
    '<w:abstractNum xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:abstractNumId="{a}">'
    '<w:multiLevelType w:val="hybridMultilevel"/>'
    '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="-"/><w:lvlJc w:val="left"/>'
    '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>'
    '<w:rPr><w:rFonts w:ascii="Century Gothic" w:hAnsi="Century Gothic" w:hint="default"/></w:rPr></w:lvl>'
    '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="o"/><w:lvlJc w:val="left"/>'
    '<w:pPr><w:ind w:left="1440" w:hanging="360"/></w:pPr>'
    '<w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New" w:hint="default"/></w:rPr></w:lvl>'
    '</w:abstractNum>')


def add_dash_list(doc):
    """Add the IXL "-" / "o" bullet list to numbering.xml; return its numId."""
    from docx.oxml import parse_xml
    from docx.oxml.ns import qn
    numbering = doc.part.numbering_part.element
    a = max([int(e.get(qn('w:abstractNumId'))) for e in numbering.findall(qn('w:abstractNum'))] + [-1]) + 1
    n = max([int(e.get(qn('w:numId'))) for e in numbering.findall(qn('w:num'))] + [0]) + 1
    first_num = numbering.find(qn('w:num'))
    abstract = parse_xml(LIST_XML.format(a=a))
    if first_num is not None:
        first_num.addprevious(abstract)
    else:
        numbering.append(abstract)
    numbering.append(parse_xml(
        f'<w:num xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:numId="{n}">'
        f'<w:abstractNumId w:val="{a}"/></w:num>'))
    return n


def write_bullets(docx_path, spec):
    """Rewrite each step's text cell as a real Word bullet list ("-", sub "o"),
    Century Gothic 14 pt, so Enter in Word continues the list. fill.py stays untouched."""
    from docx import Document
    from docx.oxml import parse_xml
    from docx.shared import Pt
    doc = Document(str(docx_path))
    num_id = add_dash_list(doc)
    spp = spec['steps_per_page']
    grids = [t for t in doc.tables if len(t.rows) >= 3]
    for i, step in enumerate(spec['steps']):
        t = grids[i // spp]
        cols = len(t.columns)
        slot = i % spp
        cell = t.rows[(slot // cols) * 3 + 2].cells[slot % cols]
        for p in cell.paragraphs[1:]:
            p._element.getparent().remove(p._element)
        first = True
        for lvl, line in bullets(step['text']):
            para = cell.paragraphs[0] if first else cell.add_paragraph()
            if first:
                for r in list(para.runs):
                    r._element.getparent().remove(r._element)
                first = False
            ppr = para._p.get_or_add_pPr()
            ppr.insert(0, parse_xml(
                '<w:numPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f'<w:ilvl w:val="{lvl}"/><w:numId w:val="{num_id}"/></w:numPr>'))
            para.paragraph_format.space_before = para.paragraph_format.space_after = Pt(0)
            run = para.add_run(line)
            run.font.name = 'Century Gothic'
            run.font.size = Pt(TEXT_PT)
            sz = parse_xml('<w:rPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                           f'<w:sz w:val="{TEXT_PT * 2}"/><w:szCs w:val="{TEXT_PT * 2}"/></w:rPr>')
            ppr.append(sz)  # paragraph mark size = bullet size
    doc.save(str(docx_path))


def verify(docx_path, spec):
    from docx import Document
    from docx.oxml.ns import qn
    doc = Document(str(docx_path))
    n, spp = len(spec['steps']), spec['steps_per_page']
    grids = [t for t in doc.tables if len(t.rows) >= 3]
    if len(grids) != math.ceil(n / spp):
        fail(f'Expected {math.ceil(n / spp)} step tables, found {len(grids)}.')
    pics = sum(len(t._tbl.findall('.//' + qn('w:drawing'))) for t in grids)
    if pics != n:
        fail(f'Expected {n} photos, found {pics}.')
    title = doc.sections[0].header.tables[0].rows[1].cells[-1].text
    if (spec['part'].get('title') or spec['part']['name']) not in title:
        fail('Header title not set.')
    return f'verified: {len(grids)} page(s), {pics} photos, title "{title.strip()}"'


def render_pages(docx_path, expected):
    office = shutil.which('soffice') or shutil.which('libreoffice')
    if not office:
        return 'render skipped: no LibreOffice (Word is the final check).'
    outdir = docx_path.parent / 'render'
    outdir.mkdir(exist_ok=True)
    subprocess.run([office, '--headless', '--convert-to', 'pdf', '--outdir', str(outdir), str(docx_path)],
                   check=True, capture_output=True, timeout=180)
    pdf = outdir / docx_path.with_suffix('.pdf').name
    if shutil.which('pdftoppm'):
        subprocess.run(['pdftoppm', '-r', '60', '-png', str(pdf), str(outdir / docx_path.stem)], check=True, timeout=120)
    info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True).stdout if shutil.which('pdfinfo') else ''
    m = re.search(r'Pages:\s+(\d+)', info)
    pages = int(m.group(1)) if m else 0
    font = subprocess.run(['fc-match', 'Century Gothic'], capture_output=True, text=True).stdout if shutil.which('fc-match') else ''
    note = '' if re.search(r'gothic', font, re.I) else ' (Century Gothic missing: page count unreliable, see SKILL.md)'
    if pages > expected:
        return f'WARNING rendered {pages} pages, expected {expected}: shorten part.title (one header line) or use more steps per page{note}. {outdir}'
    return f'rendered {pages} page(s): {outdir}{note}'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=['prep', 'preview', 'approve', 'export'])
    ap.add_argument('spec')
    ap.add_argument('--note', default='')
    ap.add_argument('--render', action='store_true')
    a = ap.parse_args()
    try:
        if a.command == 'approve':
            print(approve(a.spec, a.note))
        elif a.command == 'export':
            print(export(a.spec, a.render))
        else:
            print(globals()[a.command](a.spec))
    except (ValueError, FileNotFoundError, KeyError) as e:
        ap.exit(1, f'SOP: {e}\n')


if __name__ == '__main__':
    main()
