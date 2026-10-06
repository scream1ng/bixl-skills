#!/usr/bin/env python3
"""Design board: one self-contained, full-quality HTML page per job (brief, pictures, elements, stages, decisions)."""
import argparse
import base64
import html
import json
import mimetypes
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Blocked(Exception):
    pass


def embed(path, base):
    """Return a data URI for an image at full quality; a missing file blocks the board."""
    p = (base / path) if not Path(path).is_absolute() else Path(path)
    if not p.is_file(): raise Blocked(f'missing image: {path}')
    mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    if not mime.startswith('image/'): raise Blocked(f'not an image: {path}')
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode('ascii')


def esc(text):
    return html.escape(str(text if text is not None else ''))


def bullets(items):
    return '<ul>' + ''.join(f'<li>{esc(i)}</li>' for i in items) + '</ul>' if items else ''


def figure(img, base):
    return (f'<figure><img src="{embed(img["src"], base)}" alt="{esc(img.get("caption", ""))}" loading="lazy">'
            f'<figcaption>{esc(img.get("caption", ""))}</figcaption></figure>')


def compare(pair, base):
    """Before/after slider: b is drawn over a and clipped by the range input."""
    return (f'<figure class="cmp"><div class="cmpbox"><img src="{embed(pair["a"], base)}" alt="">'
            f'<div class="top"><img src="{embed(pair["b"], base)}" alt=""></div></div>'
            f'<input type="range" min="0" max="100" value="50" aria-label="Compare">'
            f'<figcaption><b>{esc(pair.get("a_label", "A"))}</b> ◀ ▶ <b>{esc(pair.get("b_label", "B"))}</b>'
            f' · {esc(pair.get("caption", ""))}</figcaption></figure>')


def element_cards(elements, base):
    status = {'pending': 'pending', 'agreed': 'agreed', None: 'open'}
    cards = []
    for i, e in enumerate(elements, 1):
        pic = f'<img src="{embed(e["image"], base)}" alt="">' if e.get('image') else ''
        st = e.get('status') or ('agreed' if e.get('source') in ('provided', 'measured') else None)
        cards.append(f'<div class="card">{pic}<div><b>{i}. {esc(e["id"])} {esc(e["name"])}</b>'
                     f'<span>{esc(e.get("value", ""))}</span><small class="src">{esc(e.get("source", "?"))}</small>'
                     f'<small class="st {status.get(st, "open")}">{esc(st or "to confirm")}</small></div></div>')
    return '<div class="cards">' + ''.join(cards) + '</div>'


def build(board_path, out_path=None):
    board_path = Path(board_path); base = board_path.parent
    b = json.loads(board_path.read_text())
    out = Path(out_path) if out_path else base / 'board.html'
    out.unlink(missing_ok=True)  # never leave a stale board behind a block
    parts = [f'<header><h1>{esc(b.get("project", ""))}</h1><p class="meta">{esc(b.get("revision", ""))} · '
             f'stage: <b>{esc(b.get("stage", ""))}</b></p>{bullets(b.get("next", []))}</header>']
    nav = []
    if b.get('brief'):
        parts.append(f'<section id="brief"><h2>Brief</h2>{bullets(b["brief"])}</section>'); nav.append(('brief', 'Brief'))
    for k, s in enumerate(b.get('sections', [])):
        sid = f's{k}'; nav.append((sid, s['title']))
        body = bullets(s.get('bullets', []))
        body += ''.join(compare(c, base) for c in s.get('compare', []))
        if s.get('images'): body += '<div class="grid">' + ''.join(figure(i, base) for i in s['images']) + '</div>'
        parts.append(f'<section id="{sid}"><h2>{esc(s["title"])}</h2>{body}</section>')
    if b.get('elements'):
        if not (base / b['elements']).is_file(): raise Blocked(f'missing elements: {b["elements"]}')
        spec = json.loads((base / b['elements']).read_text())
        parts.append(f'<section id="elements"><h2>Elements</h2>{element_cards(spec.get("elements", []), base)}</section>')
        nav.append(('elements', 'Elements'))
    if b.get('viewer'):
        page = (base / b['viewer'])
        if not page.is_file(): raise Blocked(f'missing viewer: {b["viewer"]}')
        parts.append(f'<section id="viewer"><h2>3D review</h2><iframe srcdoc="{html.escape(page.read_text(), quote=True)}"'
                     f' title="3D review" allow="clipboard-write"></iframe></section>'); nav.append(('viewer', '3D'))
    if b.get('decisions') or b.get('open'):
        dec = ''.join(f'<li><small>{esc(d.get("date", ""))}</small> {esc(d["text"])}</li>' for d in b.get('decisions', []))
        parts.append(f'<section id="decisions"><h2>Decisions</h2><ul class="dec">{dec}</ul>'
                     + (f'<h3>Open</h3>{bullets(b["open"])}' if b.get('open') else '') + '</section>')
        nav.append(('decisions', 'Decisions'))
    links = ''.join(f'<a href="#{i}">{esc(t)}</a>' for i, t in nav)
    page = (ROOT / 'assets/board.html').read_text().replace('__TITLE__', esc(b.get('project', 'Design board'))) \
        .replace('__NAV__', links).replace('__BODY__', ''.join(parts))
    out.write_text(page)
    return {'board': str(out.resolve()), 'bytes': len(page.encode()), 'sections': len(nav)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('board', help='board.json')
    p.add_argument('--out', help='default: board.html beside board.json')
    a = p.parse_args()
    try:
        print(json.dumps(build(a.board, a.out), indent=2))
    except Blocked as error:
        print(json.dumps({'blocked': str(error)}, indent=2)); sys.exit(2)
