#!/usr/bin/env python3
"""Pin clearance screen: every pin_locators pin stays clear of all fixture plates but its own pad.

A pin's host pad is the one plate with the largest contact under the pin base along the master part's
primary datum normal (the unload direction). Any overlap with a plate, or a gap under MIN_GAP_MM to any
other plate (cap tabs through the pad, cheeks, braces), is a fail: the pin cannot be ground, screwed or
welded down. A sliding/removable pin may instead seat on its REF_BUSH_/REF_CARRIER_ solid; the plate that
solid is mounted on is then exempt from the gap.
"""
from __future__ import annotations

import numpy as np
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut

from unload_path import direction
from verify import PLATE_VOL, bbox, common_volume, gap, moved

MIN_GAP_MM, SINK_MM = 5.0, 0.05


def near(a, b, pad):
    return all(a[i] <= b[i + 3] + pad and b[i] <= a[i + 3] + pad for i in range(3))


def audit(spec, shapes):
    leaf = lambda n: n.split('/')[-1]
    plates = {n: s for n, s in shapes.items() if leaf(n) in {p['name'] for p in spec.get('plates', [])}}
    wanted = {p['shape_name']: p.get('id', p['shape_name']) for p in spec.get('pin_locators', []) if p.get('shape_name')}
    withdrawn = {p.get('id', p['shape_name']) for p in spec.get('pin_locators', []) if p.get('mode') in ('sliding', 'removable')}
    supports = {n: s for n, s in shapes.items() if leaf(n).startswith(('REF_BUSH_', 'REF_CARRIER_'))}
    pins = {wanted[leaf(n)]: s for n, s in shapes.items() if leaf(n) in wanted}
    parts = {n: s for n, s in shapes.items() if leaf(n).startswith('Part_')}
    _, d = direction(spec, parts) if parts else (None, None)
    d = np.array([0.0, 0.0, 1.0]) if d is None else d
    base = {'min_gap_mm': MIN_GAP_MM, 'direction': d.round(4).tolist(),
            'scope': 'nominal CAD; host pad = plate with the largest contact under the pin base'}
    if not pins:
        return {**base, 'status': 'unknown', 'pins': [], 'violations': [],
                'next_action': 'List every pin in pin_locators with the shape_name of its REF_ solid.'}
    rows, bad = [], []
    for pid, pin in pins.items():
        pb, sunk = bbox(pin), BRepAlgoAPI_Cut(moved(pin, -d * SINK_MM), pin).Shape()  # thin slab under the base
        seats = {**plates, **supports} if pid in withdrawn else plates
        close = {n: s for n, s in seats.items() if near(pb, bbox(s), MIN_GAP_MM)}
        seat = {n: common_volume(sunk, s) for n, s in close.items()}
        host = max(seat, key=seat.get) if seat and max(seat.values()) > 0 else None
        hosts, closest = [host] if host else [], None
        mount = {n for n, s in plates.items() if host in supports and gap(supports[host], s) < SINK_MM}
        for name, plate in close.items():
            if name == host or name in mount or name in supports: continue
            g = gap(pin, plate)
            v = common_volume(pin, plate) if g < MIN_GAP_MM else 0.0
            if v > PLATE_VOL or g < MIN_GAP_MM:
                bad.append({'pin': pid, 'plate': name, 'gap_mm': round(g, 2), 'overlap_mm3': round(v, 3)})
            if closest is None or g < closest[1]: closest = (name, round(g, 2))
        v = common_volume(pin, seats[host]) if host else 0.0
        if v > PLATE_VOL: bad.append({'pin': pid, 'plate': host, 'gap_mm': 0.0, 'overlap_mm3': round(v, 3)})
        rows.append({'pin': pid, 'host': hosts, 'closest': closest,
                     'status': 'fail' if any(b['pin'] == pid for b in bad) or not hosts else 'pass'})
    orphan = [r['pin'] for r in rows if not r['host']]
    status = 'fail' if bad or orphan else 'pass'
    action = None
    if status == 'fail':
        parts_ = [f"move pin or relieve/move {b['plate']} ({b['pin']} gap {b['gap_mm']} mm)" for b in bad]
        parts_ += [f'seat {p} on a pad plate below its base' for p in orphan]
        action = f'Keep pins >= {MIN_GAP_MM:g} mm from tabs, cheeks and braces: ' + '; '.join(parts_) + '.'
    return {**base, 'status': status, 'pins': rows, 'violations': bad, 'unseated': orphan, 'next_action': action}
