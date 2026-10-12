"""Check rendered annotation footprints after all view transforms.

Own balloon leaders may enter their own badge. A dimension's value mask may
cover its own dimension line. No other badge/text intersections are allowed.
CAD geometry is excluded: annotation targets intentionally touch the part.
"""
import math
import re


def intersects(box, a, b):
    """Clip any finite segment against an axis-aligned rectangle."""
    lo, hi = 0.0, 1.0
    for axis in (0, 1):
        delta = b[axis] - a[axis]
        if abs(delta) < 1e-12:
            if not box[axis] <= a[axis] <= box[axis + 2]:
                return False
        else:
            start = (box[axis] - a[axis]) / delta
            end = (box[axis + 2] - a[axis]) / delta
            lo, hi = max(lo, min(start, end)), min(hi, max(start, end))
            if lo > hi:
                return False
    return True


def arc_segments(node):
    # The renderer emits circular SVG arcs, rotation 0, absolute M/A only.
    values = re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?', node.get('d', ''))
    if len(values) != 9:
        raise ValueError('Unsupported annotation arc in clearance check.')
    x, y, radius, ry, rotation, large, sweep, ex, ey = map(float, values)
    if radius != ry or rotation != 0:
        raise ValueError('Clearance check requires circular annotation arcs.')
    dx, dy = ex - x, ey - y
    chord = math.hypot(dx, dy)
    h = math.sqrt(max(0, radius * radius - chord * chord / 4))
    sign = -1 if bool(large) == bool(sweep) else 1
    cx = (x + ex) / 2 - sign * dy * h / chord
    cy = (y + ey) / 2 + sign * dx * h / chord
    start = math.atan2(y - cy, x - cx)
    end = math.atan2(ey - cy, ex - cx)
    angle = (end - start) % (2 * math.pi) if sweep else -((start - end) % (2 * math.pi))
    # <=2-pixel chords; the 3-pixel clearance margin covers chord approximation.
    steps = max(2, math.ceil(abs(angle) * radius / 2))
    points = [(cx + radius * math.cos(start + angle * i / steps),
               cy + radius * math.sin(start + angle * i / steps)) for i in range(steps + 1)]
    return list(zip(points, points[1:]))


def validate(root, padding=3):
    boxes, segments = [], []
    width, height = map(float, root.get('viewBox').split()[2:])
    for owner, group in enumerate(n for n in root.iter() if n.get('data-check')):
        name = group.get('data-check')
        for node in group:
            tag = node.tag.split('}')[-1]
            if tag == 'rect':
                x, y, w, h = (float(node.get(k)) for k in ('x', 'y', 'width', 'height'))
                if x < 0 or y < 0 or x + w > width or y + h > height:
                    raise ValueError(f'Annotation clipped at drawing edge: {name}.')
                badge = node.get('stroke') is not None
                boxes.append((owner, name, badge, (x, y, x + w, y + h), group.get('data-checks') is None))
            elif tag == 'line':
                a = tuple(float(node.get(k)) for k in ('x1', 'y1'))
                b = tuple(float(node.get(k)) for k in ('x2', 'y2'))
                segments.append((owner, name, False, a, b))
            elif tag in ('polyline','polygon'):
                points = [tuple(map(float, p.split(','))) for p in node.get('points').split()]
                if tag=='polygon':points.append(points[0])
                segments.extend((owner, name, tag=='polyline', a, b) for a, b in zip(points, points[1:]) if a != b)
            elif tag == 'path':
                segments.extend((owner, name, False, a, b) for a, b in arc_segments(node))
    for i, (owner, name, badge, box, dimension) in enumerate(boxes):
        expanded = (box[0] - padding, box[1] - padding, box[2] + padding, box[3] + padding)
        for _, other_name, _, other, _ in boxes[:i]:
            if expanded[0] <= other[2] and other[0] <= expanded[2] and expanded[1] <= other[3] and other[1] <= expanded[3]:
                raise ValueError(f'Annotation badges/values overlap: {name} and {other_name}.')
        for other_owner, other_name, leader, a, b in segments:
            if owner == other_owner and ((not badge and dimension) or (badge and leader)):
                continue
            if intersects(expanded, a, b):
                raise ValueError(f'Annotation {name} intersects a line for {other_name}; move its badge/value or route.')
    return {'labels_checked': len(boxes), 'segments_checked': len(segments), 'clearance_px': padding}
