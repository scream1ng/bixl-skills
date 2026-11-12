#!/usr/bin/env python3
"""Run one costing at several batch quantities and bundle the results for render_report.py.

Usage: python3 quote.py QUOTE.json --out QUOTE_RESULT.json
(also writes QUOTE_RESULT_Q<n>.json, the plain calculator result for each quantity, for compare.py)

QUOTE.json = {"quantities": [...], "base": <schema-2 input without quantity>,
              "stock": [...optional sheet stock groups...], "scenarios": [...optional...]}
For each quantity, every stock group adds: one shared sheet-material row (consumed sheet
equivalents), one shared laser-setup row, and the sheet load/unload time inside each listed
laser run row (10 min per whole sheet handled, spread over the parts). See
references/calculator-contract.md "Quote file".
"""
import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calculate import calculate, fields, number, text  # noqa: E402

CONFIG = json.loads((Path(__file__).resolve().parent.parent / 'references/rates.json').read_text())
STOCK_REQUIRED = ('id', 'description', 'sheet_price', 'sheet_size_mm', 'price_basis', 'parts')
STOCK_OPTIONAL = ('material_no', 'moq_sheets', 'handling_minutes', 'laser_resource', 'setup_h_per_program',
                  'programs', 'yield_basis')


def cumulative(components):
    nodes = {c['id']: c for c in components}
    def qty(cid):
        c = nodes[cid]
        return 1 if c['parent_id'] is None else qty(c['parent_id']) * c['quantity_per_parent']
    return {cid: qty(cid) for cid in nodes}


def rate(resource):
    r = CONFIG['resources'][resource]
    return r['labour_per_hour'] + r['machine_per_hour']


def build(spec, q, overrides=None):
    """Schema-2 input for batch quantity q, plus display hints for the report."""
    data = copy.deepcopy(spec['base'])
    data['quantity'] = q
    rows = {r['id']: r for r in data['rows']}
    for rid, patch in (overrides or {}).items():
        if rid not in rows:
            raise ValueError(f'Scenario changes unknown row {rid}')
        rows[rid].update(copy.deepcopy(patch))
    cum = cumulative(data['components'])
    display = {'setup_rows': {}, 'stock': {}, 'handling': {}}
    for st in spec.get('stock', []):
        fields(st, STOCK_REQUIRED, STOCK_OPTIONAL)
        sid = text(st['id'], 'stock id')
        price = number(st['sheet_price'], 'sheet_price')
        minutes = number(st.get('handling_minutes', CONFIG.get('laser_sheet_handling_minutes_default', 10)), 'handling_minutes')
        res = st.get('laser_resource', 'laser')
        setup_h = number(st.get('setup_h_per_program', 0.25), 'setup_h_per_program')
        parts = st['parts']
        if not isinstance(parts, dict) or not parts:
            raise ValueError(f'Stock {sid} needs parts')
        units, consumed = {}, 0.0
        for cid, p in parts.items():
            fields(p, ('per_sheet',), ('laser_row',))
            if cid not in cum:
                raise ValueError(f'Stock {sid} lists unknown component {cid}')
            n = number(p['per_sheet'], 'per_sheet', positive=True, integer=True)
            units[cid] = q * cum[cid]
            consumed += units[cid] / n
        sheets = math.ceil(consumed - 1e-9)
        hf = sheets / consumed                      # whole sheets handled / sheet equivalents used
        shares = {cid: (units[cid] / parts[cid]['per_sheet']) / consumed for cid in parts}
        fix = 1 - sum(shares.values()); k = max(shares, key=shares.get); shares[k] += fix
        handled = 0.0
        for cid, p in parts.items():
            lr = p.get('laser_row')
            if not lr:
                continue
            row = rows.get(lr)
            if not row or row['kind'] != 'process' or row.get('component_id') != cid:
                raise ValueError(f'Laser row {lr} must be a process row on {cid}')
            if row['setup_h'] or row['setup_count']:
                raise ValueError(f'Laser row {lr}: set setup to 0; quote.py adds the shared program setup')
            secs = {kk: v for kk, v in row['cycle_seconds'].items() if kk != 'sheet_load_unload'}
            secs['sheet_load_unload'] = minutes * 60 / p['per_sheet'] * hf
            row['cycle_seconds'] = secs
            row['pcs_per_h'] = 3600 / sum(secs.values())
            handled += units[cid] * secs['sheet_load_unload']
            display['handling'][lr] = {'per_sheet': p['per_sheet'], 'seconds': secs['sheet_load_unload'],
                                       'program_seconds': sum(secs.values()) - secs['sheet_load_unload']}
        laser_parts = [cid for cid, p in parts.items() if p.get('laser_row')]
        if laser_parts and not math.isclose(handled, sheets * minutes * 60, rel_tol=1e-9):
            raise ValueError(f'Stock {sid}: handling charged {handled:.1f} s, sheets handled need {sheets * minutes * 60:.1f} s')
        data['rows'].append({
            'id': f'{sid}-material', 'name': st['description'], 'kind': 'shared_batch', 'category': 'material',
            'allocations': shares, 'charge_scope': f'{sid}-material',
            'basis': f"{st['price_basis']}; {st.get('yield_basis', 'parts per sheet as listed')}; {consumed:.3f} sheet equivalents used",
            'batch_cost': price * consumed,
            'procurement': {'sheet_price': price, 'consumed_sheet_equivalents': consumed, 'purchase_sheets': sheets,
                            'basis': f"Whole sheets for this batch; listed MOQ {st.get('moq_sheets', 'unknown')} sheets"}})
        if laser_parts:
            progs = st.get('programs', min(len(laser_parts), sheets))
            number(progs, 'programs', positive=True, integer=True)
            cost = progs * setup_h * rate(res)
            share = {cid: 1 / len(laser_parts) for cid in laser_parts}
            fix = 1 - sum(share.values()); share[laser_parts[0]] += fix
            data['rows'].append({
                'id': f'{sid}-laser-setup', 'name': 'Laser', 'kind': 'shared_batch', 'category': 'component_processing',
                'allocations': share, 'charge_scope': f'{sid}-laser-setup',
                'basis': f'{setup_h:g} h per program x {progs} programs (part numbers, capped at sheets in the batch), shared equally',
                'batch_cost': cost, 'setup_batch_cost': cost})
            display['setup_rows'][f'{sid}-laser-setup'] = {'resource': res, 'hours_total': progs * setup_h,
                                                           'shares': share, 'label': 'Laser'}
        for cid, p in parts.items():
            display['stock'][cid] = {'stock_id': sid, 'per_sheet': p['per_sheet'], 'description': st['description'],
                                     'material_no': st.get('material_no'), 'sheet_price': price,
                                     'row_id': f'{sid}-material'}
        display.setdefault('sheets', {})[sid] = {'consumed': consumed, 'purchase_sheets': sheets,
                                                 'outlay': sheets * price, 'moq_sheets': st.get('moq_sheets')}
    return data, display


def run(spec):
    fields(spec, ('quantities', 'base'), ('stock', 'scenarios'))
    qs = spec['quantities']
    if not isinstance(qs, list) or not qs or len(set(qs)) != len(qs):
        raise ValueError('quantities must be a list of distinct positive integers')
    if 'quantity' in spec['base']:
        raise ValueError('Leave quantity out of base; quote.py sets it per quantity')
    out = {'job': spec['base'].get('job'), 'revision': spec['base'].get('revision'), 'quantities': {}, 'scenarios': []}
    for q in qs:
        number(q, 'quantity', positive=True, integer=True)
        data, display = build(spec, q)
        out['quantities'][str(q)] = {'result': calculate(data), 'display': display}
    for sc in spec.get('scenarios', []):
        fields(sc, ('label', 'quantity', 'rows'))
        data, display = build(spec, sc['quantity'], sc['rows'])
        r = calculate(data)
        out['scenarios'].append({'label': text(sc['label'], 'scenario label'), 'quantity': sc['quantity'],
                                 'per_assembly': r['per_assembly'], 'selling_per_assembly': r['selling_per_assembly']})
    return out


if __name__ == '__main__':
    try:
        if len(sys.argv) != 4 or sys.argv[2] != '--out':
            sys.exit('Usage: quote.py QUOTE.json --out QUOTE_RESULT.json')
        res = run(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
        out = Path(sys.argv[3])
        out.write_text(json.dumps(res, indent=1, allow_nan=False) + '\n', encoding='utf-8')
        for q, v in res['quantities'].items():          # one calculator result per quantity, for compare.py
            out.with_name(f'{out.stem}_Q{q}.json').write_text(json.dumps(v['result'], indent=1, allow_nan=False) + '\n', encoding='utf-8')
        print(json.dumps({q: {'per_assembly': round(v['result']['per_assembly'], 2),
                              'selling_per_assembly': round(v['result']['selling_per_assembly'], 2),
                              'status': v['result']['status']} for q, v in res['quantities'].items()}, indent=1))
    except (KeyError, ValueError, TypeError, OSError) as error:
        sys.exit(f'Input error: {error}')
