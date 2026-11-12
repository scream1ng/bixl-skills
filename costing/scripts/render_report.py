#!/usr/bin/env python3
"""Quote-sheet HTML from quote.py results.

Usage: python3 render_report.py QUOTE_RESULT.json REPORT_META.json --out JOB-costing.html

Every figure comes from the calculator results; this script only arranges them. One tab per
top-level assembly (children of the root that have children of their own), components shown in
build order (children before parents), then Summary and Basis tabs. See references/report-format.md.
"""
import base64
import html
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE.parent / 'references/rates.json').read_text())
TEMPLATE = HERE.parent / 'assets/quote-sheet.html'
META_KEYS = {'unit_plural', 'title', 'customer', 'date', 'revision', 'material', 'unit_label', 'default_quantity', 'header',
             'parts', 'notes', 'warning', 'currency'}
PART_KEYS = {'desc', 'spec', 'image', 'nest_svg', 'nest_json'}


def esc(v):
    return html.escape(str(v), quote=True)


def op_label(name):
    return re.sub(r'^OP\d+\s*[-—:]?\s*', '', name).strip()


def wc(resource):
    return CONFIG['resources'][resource]['name'] if resource in CONFIG['resources'] else ''


def rates(row):
    if row.get('resource') in CONFIG['resources']:
        r = CONFIG['resources'][row['resource']]
        return r['labour_per_hour'], r['machine_per_hour']
    return row.get('hourly_rate'), None


def data_uri(path):
    p = Path(path)
    mime = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}.get(p.suffix.lower())
    if not mime:
        raise ValueError(f'Image must be .jpg or .png: {path}')
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()


def nest_thumb(svg_path, json_path, cid):
    svg = Path(svg_path).read_text()
    svg = re.sub(r'<text[^>]*>[^<]*</text>', '', svg)          # thumbnail: no axis numbers or labels
    svg = svg.replace('<svg ', f'<svg role="img" aria-label="Sheet nest for {esc(cid)}" ', 1)
    lay = json.loads(Path(json_path).read_text())['layouts']
    lay = lay.get(cid) or next(iter(lay.values()))
    n = sum(lay['counts'].values())
    return {'svg': svg, 'per_sheet': n, 'utilisation': lay['utilisation']}


def view(q, entry, meta):
    r, disp = entry['result'], entry['display']
    bom = {b['id']: b for b in r['bom']}
    kids = {cid: [b['id'] for b in r['bom'] if b['parent_id'] == cid] for cid in bom}
    root = r['root_id']
    units = {cid: q * bom[cid]['units_per_assembly'] for cid in bom}
    rows = r['rows']
    margin = r['gross_margin']

    def block(cid):
        u = units[cid]
        groups, extra, mat = {}, [], []
        order = []
        def grp(res):
            if res not in groups:
                groups[res] = {'setup': [], 'run': []}; order.append(res)
            return groups[res]
        for row in rows:
            share = (row.get('allocated_batch_costs') or {}).get(cid)
            owns = row.get('component_id') == cid or (row.get('allocations') and cid in row['allocations'])
            if not owns or row.get('one_off') or row.get('absorbed_in_margin'):
                continue
            if row.get('unpriced'):
                extra.append({'op': op_label(row['name']), 'wc': '', 'val': '', 'kind': 'cost', 'cost': None})
                continue
            cost = share / u
            if row['kind'] == 'process':
                lab, oh = rates(row)
                g = grp(row.get('resource', 'rate:' + str(row.get('hourly_rate'))))
                name = op_label(row['name'])
                if row['setup_batch_cost'] > 0:
                    g['setup'].append({'op': 'Setup ' + re.split(r' × |,', name)[0], 'wc': wc(row.get('resource')), 'val': row['setup_h'] * row['setup_count'],
                                       'kind': 'setup', 'lab': lab, 'oh': oh, 'cost': row['setup_batch_cost'] / u})
                note = ', incl. sheet load/unload' if 'sheet_load_unload' in row['cycle_seconds'] else ''
                g['run'].append({'op': 'Run ' + name + note, 'wc': wc(row.get('resource')), 'val': row['pcs_per_h'], 'kind': 'run',
                                 'lab': lab, 'oh': oh, 'cost': row['run_batch_cost'] / u, 'row': row['id']})
            elif row['kind'] == 'shared_batch' and row['id'] in disp['setup_rows']:
                d = disp['setup_rows'][row['id']]; res = d['resource']; rr = CONFIG['resources'][res]
                grp(res)['setup'].insert(0, {'op': 'Setup ' + d['label'], 'wc': wc(res), 'val': d['hours_total'] * d['shares'][cid],
                                            'kind': 'setup', 'lab': rr['labour_per_hour'], 'oh': rr['machine_per_hour'], 'cost': cost})
            elif row['kind'] == 'shared_batch' and row['category'] == 'material' and cid in disp['stock']:
                s = disp['stock'][cid]
                mat.append({'d': s['description'], 'num': ('BIXL ' + s['material_no']) if s.get('material_no') else '',
                            'q': f"{s['per_sheet']} pcs/sheet", 'u': f"${s['sheet_price']:,.2f} /sheet", 'cost': cost})
            elif row['kind'] == 'material':
                mat.append({'d': row['name'], 'num': '', 'q': f"{row['parts_per_sheet']} pcs/sheet",
                            'u': f"${row['sheet_price']:,.2f} /sheet", 'cost': cost})
            elif row['kind'] == 'fixed' and row['category'] == 'material':
                mat.append({'d': row['name'], 'num': '', 'q': '1', 'u': f"${row['unit_price']:,.2f} each", 'cost': cost})
            else:
                extra.append({'op': op_label(row['name']), 'wc': '', 'val': '', 'kind': 'cost', 'cost': cost})
        prod = [x for res in order for x in groups[res]['setup'] + groups[res]['run']] + extra
        comps = [{'id': k, 'd': bom[k]['name'], 'q': bom[k]['quantity_per_parent'], 'u': bom[k]['unit_cost'],
                  'cost': bom[k]['unit_cost'] * bom[k]['quantity_per_parent']} for k in kids[cid]]
        laser = next((disp['handling'][x['row']] for x in prod if x.get('row') in disp['handling']), None)
        unpriced = any(x['cost'] is None for x in prod)
        total = sum(x['cost'] for x in prod if x['cost'] is not None) + sum(m['cost'] for m in mat) + sum(c['cost'] for c in comps)
        if not math.isclose(total, bom[cid]['unit_cost'], abs_tol=0.005):
            raise ValueError(f'{cid}: displayed rows {total:.4f} do not add to calculator unit cost {bom[cid]["unit_cost"]:.4f}')
        return {'id': cid, 'name': bom[cid]['name'], 'prod': prod, 'mat': mat, 'comps': comps, 'unpriced': unpriced,
                'total': bom[cid]['unit_cost'], 'per_root': bom[cid]['units_per_assembly'],
                'laser': laser and {'program': laser['program_seconds'], 'handling': laser['seconds']}}

    def walk(cid, out):
        for k in kids[cid]:
            walk(k, out)
        out.append(cid)
        return out

    # a tab per sub-assembly: a child of the root that has a made child of its own (bought hardware does not count)
    tops = [k for k in kids[root] if any(bom[c]['make_buy'] == 'make' for c in kids[k])]
    pages = []
    for t in tops:
        seq = walk(t, [])
        pages.append({'id': t, 'name': bom[t]['name'], 'blocks': [block(c) for c in seq if bom[c]['make_buy'] == 'make' or c == t]})
    rest = [k for k in kids[root] if k not in tops]
    root_has_rows = any(row.get('component_id') == root or root in (row.get('allocations') or {}) for row in rows
                        if not row.get('absorbed_in_margin'))
    if not tops or rest or root_has_rows:
        seq = [c for k in rest for c in walk(k, [])] + [root]
        pages.append({'id': root, 'name': bom[root]['name'], 'blocks': [block(c) for c in seq if bom[c]['make_buy'] == 'make' or c == root]})
    for p in pages:
        steps = {b['id']: i + 1 for i, b in enumerate(p['blocks'])}
        for b in p['blocks']:
            b['step'] = steps[b['id']]
            b['refs'] = [steps[c['id']] for c in b['comps'] if c['id'] in steps]
            for c in b['comps']:
                c['ref'] = steps.get(c['id'])
        top = p['blocks'][-1]
        top['sell'] = top['total'] / (1 - margin)
        top['sell_root'] = top['sell'] * top['per_root']
    roll = [{'name': bom[k]['name'], 'n': bom[k]['units_per_assembly'], 'cost': bom[k]['per_assembly'],
             'sell': bom[k]['per_assembly'] / (1 - margin)} for k in kids[root]]
    own_root = bom[root]['own_batch_cost'] / q
    if own_root > 1e-9:
        roll.append({'name': 'Final assembly and dispatch', 'n': 1, 'cost': own_root, 'sell': own_root / (1 - margin)})
    sheets = list(disp.get('sheets', {}).values())
    proc = r['procurement']
    return {'Q': q, 'cost': r['per_assembly'], 'sell': r['selling_per_assembly'], 'bcost': r['batch_cost'],
            'bsell': r['selling_batch'], 'profit': r['profit_per_assembly'], 'margin': margin,
            'absorbed': r['absorbed_per_assembly'], 'eff': r['effective_margin'], 'status': r['status'],
            'unpriced': [row['name'] for row in rows if row.get('unpriced')],
            'sheets': sum(s['purchase_sheets'] for s in sheets) if sheets else sum(p.get('whole_sheets_required', 0) for p in proc),
            'roll': roll, 'pages': pages,
            'basis': [{'name': op_label(row['name']), 'basis': row['basis']} for row in rows]}


def render(qres, meta, out):
    extra = set(meta) - META_KEYS
    if extra:
        raise ValueError(f'Unknown report meta fields: {sorted(extra)}')
    for cid, p in meta.get('parts', {}).items():
        if set(p) - PART_KEYS:
            raise ValueError(f'Unknown fields for part {cid}: {sorted(set(p) - PART_KEYS)}')
    views = {q: view(int(q), e, meta) for q, e in qres['quantities'].items()}
    imgs, nests = {}, {}
    for cid, p in meta.get('parts', {}).items():
        if p.get('image'):
            imgs[cid] = data_uri(p['image'])
        if p.get('nest_svg') and p.get('nest_json'):
            nests[cid] = nest_thumb(p['nest_svg'], p['nest_json'], cid)
    blob = {'meta': {k: meta.get(k) for k in ('title', 'customer', 'date', 'revision', 'material', 'unit_label', 'unit_plural', 'header',
                                              'notes', 'warning', 'currency')},
            'parts': {cid: {k: p.get(k) for k in ('desc', 'spec')} for cid, p in meta.get('parts', {}).items()},
            'views': views, 'img': imgs, 'nest': nests, 'scenarios': qres.get('scenarios', []),
            'start': str(meta.get('default_quantity', next(iter(views))))}
    if blob['start'] not in views:
        raise ValueError('default_quantity must be one of the quoted quantities')
    page = TEMPLATE.read_text().replace('/*QUOTE*/null', json.dumps(blob, separators=(',', ':')).replace('</', '<\\/'))
    page = page.replace('<title>Quote sheet</title>', f"<title>{esc(meta.get('title', 'Quote sheet'))} costing</title>")
    ids = re.findall(r'\bid="([^"]+)"', page)
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate element ids in the page; nest drawings would show the wrong part')
    Path(out).write_text(page, encoding='utf-8')
    return len(page.encode())


if __name__ == '__main__':
    try:
        if len(sys.argv) != 5 or sys.argv[3] != '--out':
            sys.exit('Usage: render_report.py QUOTE_RESULT.json REPORT_META.json --out PAGE.html')
        size = render(json.loads(Path(sys.argv[1]).read_text()), json.loads(Path(sys.argv[2]).read_text()), sys.argv[4])
        print(f'{sys.argv[4]} {size:,} bytes')
    except (KeyError, ValueError, TypeError, OSError) as error:
        sys.exit(f'Report error: {error}')
