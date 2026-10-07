#!/usr/bin/env python3
"""Build one visual review board: Review, Elements, Revision History."""
import argparse
import base64
import html
import json
import mimetypes
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASES = {'concept': 'concept · appearance only', 'cad': 'preliminary CAD',
         'final': 'final CAD', 'photo': 'supplied photo'}

class Blocked(Exception):
    pass

def esc(value):
    return html.escape(str(value if value is not None else ''), quote=True)

def embed(path, base):
    p = base / path
    if not p.is_file():
        raise Blocked(f'missing image: {path}')
    mime = mimetypes.guess_type(p.name)[0] or ''
    if not mime.startswith('image/'):
        raise Blocked(f'not an image: {path}')
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode('ascii')

def basis(value):
    if value not in BASES:
        raise Blocked(f'image basis must be one of {", ".join(BASES)}')
    return f'<b class="basis">{BASES[value]}</b>'

def bullets(items):
    return '<ul>' + ''.join(f'<li>{esc(x)}</li>' for x in items) + '</ul>' if items else ''

def figure(img, base):
    label = basis(img.get('basis'))
    return (f'<figure><button class="zoom-image" aria-label="Enlarge {esc(img.get("caption", "image"))}">'
            f'<img src="{embed(img["src"], base)}" alt="{esc(img.get("caption", ""))}" loading="lazy"></button>'
            f'<figcaption>{label} {esc(img.get("caption", ""))}</figcaption></figure>')

def compare(pair, base):
    # Both sides must identify their evidence, including in comparisons.
    a = {'src': pair['a'], 'basis': pair.get('a_basis'), 'caption': pair.get('a_label', 'Before')}
    b = {'src': pair['b'], 'basis': pair.get('b_basis'), 'caption': pair.get('b_label', 'After')}
    return f'<div class="comparison"><div class="visuals">{figure(a, base)}{figure(b, base)}</div><p>{esc(pair.get("caption", ""))}</p></div>'

def element_cards(elements, base, final=False):
    cards = []
    seen = set()
    for e in elements:
        eid = e.get('id', '')
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', eid) or eid in seen:
            raise Blocked(f'element id must be unique and HTML-safe: {eid}')
        seen.add(eid)
        if not e.get('image'):
            raise Blocked(f'{eid}: a clean feature snapshot is required')
        label = basis(e.get('image_basis'))
        if final and e['image_basis'] != 'final':
            raise Blocked(f'{eid}: final delivery requires a snapshot of delivered geometry')
        approval = e.get('approval', 'open')
        status = e.get('status', 'modeled')
        if approval not in ('open', 'agreed', 'assumed') or status not in ('pending', 'modeled', 'verified'):
            raise Blocked(f'{eid}: invalid approval or model status')
        detail = bullets(e.get('notes', []))
        for field, title in [('assumptions', 'Assumptions'), ('questions', 'Unresolved inputs')]:
            if e.get(field):
                detail += f'<h4>{title}</h4>' + bullets(e[field])
        for d in e.get('deferrals', []):
            if not all(d.get(k) for k in ('question', 'assumption', 'approval_record')):
                raise Blocked(f'{eid}: deferral needs question, assumption and explicit approval record')
            detail += f'<h4>Approved deferral</h4>{bullets([d["question"], d["assumption"], d["approval_record"]])}'
        detail += ''.join(compare(p, base) for p in e.get('compare', []))
        detail += '<div class="visuals">' + ''.join(figure(i, base) for i in e.get('images', [])) + '</div>'
        cards.append(f'<details class="element" id="{eid}"><summary>'
            f'<span class="snapshot"><img src="{embed(e["image"], base)}" alt="{esc(e.get("image_caption", e["name"]))}" loading="lazy"></span>'
            f'<span class="eid">{eid}</span><span class="element-name">{esc(e["name"])}<small>{esc(e.get("value", ""))}</small></span><span class="plus">+</span>'
            f'<span class="evidence">{label}</span><span class="status">Source: {esc(e.get("source", "unspecified"))} · Approval: {approval} · Model: {status}</span>'
            f'</summary><div class="element-detail"><button class="enlarge-snapshot">Enlarge snapshot</button>'
            f'<button class="locate" data-element="{eid}">Locate in 3D</button>{detail}</div></details>')
    return '<div class="elements">' + ''.join(cards) + '</div>'

def history_table(rows):
    if not rows:
        raise Blocked('history needs at least the initial revision; do not invent prior revisions')
    result = '<div class="table-wrap"><table><thead><tr><th>Revision</th><th>Date</th><th>Change</th></tr></thead><tbody>'
    for r in rows:
        if not r.get('revision') or not r.get('summary'):
            raise Blocked('history entries need revision and summary')
        result += f'<tr><td>{esc(r["revision"])}</td><td>{esc(r.get("date", ""))}</td><td>{esc(r["summary"])}</td></tr>'
    return result + '</tbody></table></div>'

def build(board_path, out_path=None):
    board_path = Path(board_path)
    base = board_path.parent
    b = json.loads(board_path.read_text())
    out = Path(out_path) if out_path else base / 'board.html'
    # Do not leave a stale file at the requested output on validation failure.
    out.unlink(missing_ok=True)
    if b.get('schema_version') != 2:
        raise Blocked('migrate board.json to schema_version 2; see references/board-format.md')
    for key in ('sections', 'brief', 'next', 'decisions', 'open'):
        if b.get(key):
            raise Blocked(f'legacy {key}: move content into review, relevant elements or history; do not discard it')
    if not b.get('project') or not b.get('revision') or not b.get('board_revision'):
        raise Blocked('project, revision and board_revision are required')
    if b.get('stage') not in ('proposal', 'blockout', 'structure', 'detail', 'delivery', 'final'):
        raise Blocked('stage must be proposal, blockout, structure, detail, delivery or final')
    ep = base / b.get('elements', 'elements.json')
    if not ep.is_file():
        raise Blocked(f'missing elements: {ep}')
    elements = json.loads(ep.read_text()).get('elements', [])
    if not elements:
        raise Blocked('elements must not be empty')
    review = b.get('review', {})
    images = review.get('images', [])
    if not images:
        raise Blocked('review needs inspected images; a viewer alone is not a visual review')
    final = b.get('stage') in ('detail', 'delivery', 'final')
    if final and not any(i.get('basis') == 'final' for i in images):
        raise Blocked('delivery review needs an image from the delivered geometry')
    viewer = ''
    if b.get('viewer'):
        vp = base / b['viewer']
        if not vp.is_file():
            raise Blocked(f'missing viewer: {vp}')
        viewer = f'<iframe id="model" title="3D review" srcdoc="{esc(vp.read_text())}" allow="clipboard-write"></iframe>'
    heading = '3D Review' if viewer else 'Design Review'
    meta = f'{esc(b["project"])} · {esc(b["revision"])} · Board {esc(b["board_revision"])} · {esc(b.get("stage", "proposal"))}'
    review_body = viewer
    if review.get('recommendation'):
        review_body += f'<p class="recommendation">{esc(review["recommendation"])}</p>'
    review_body += '<div class="review-images">' + ''.join(figure(i, base) for i in images) + '</div>'
    review_body += ''.join(compare(p, base) for p in review.get('compare', []))
    review_body += bullets(review.get('notes', []))
    if viewer:
        review_body += '<p class="hint">Interactive 3D may require internet access. Embedded images remain available offline.</p>'
    body = f'<section id="review"><div class="heading"><h1>01 / {heading}</h1><p class="meta">{meta}</p></div>{review_body}</section>'
    body += '<section id="elements"><div class="heading"><h2>02 / Elements</h2><p class="meta">Snapshots, dimensions and evidence for each feature. Expand a card for detail.</p></div>'
    body += element_cards(elements, ep.parent, final) + '</section>'
    body += '<section id="history"><div class="heading"><h2>03 / Revision History</h2></div>' + history_table(b.get('history', []))
    if b.get('board_history'):
        body += '<details class="board-history"><summary>Presentation revisions</summary>' + history_table(b['board_history']) + '</details>'
    body += '</section>'
    page = (ROOT / 'assets/board.html').read_text().replace('__TITLE__', esc(b['project'])).replace('__BODY__', body)
    out.write_text(page)
    # Distinct filename for delivery avoids links reopening an older preview.
    tag = re.sub(r'[^A-Za-z0-9_-]+', '-', str(b['board_revision'])).strip('-')
    if not tag:
        raise Blocked('board_revision needs a usable filename label')
    revision_out = out.with_name(f'{out.stem}-{tag}{out.suffix}')
    revision_out.write_text(page)
    return {'board': str(out.resolve()), 'delivery_board': str(revision_out.resolve()),
            'bytes': len(page.encode()), 'sections': 3, 'elements': len(elements)}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('board', help='board.json')
    parser.add_argument('--out', help='default: board.html beside board.json')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.board, args.out), indent=2))
    except (Blocked, KeyError, ValueError) as error:
        print(json.dumps({'blocked': str(error)}, indent=2))
        sys.exit(2)
