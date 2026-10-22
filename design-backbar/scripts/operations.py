"""User-declared simultaneous bend groups, separate from shared jig identities."""
import math


def operation_sequence(value, ends):
    count=len(ends)
    if value:
        try: groups=[[int(n) for n in group.split('+')] for group in value.split(',')]
        except ValueError: raise ValueError('--sequence must list every bend once; use + for a common operation.')
        if sorted(n for group in groups for n in group)!=list(range(1,count+1)):
            raise ValueError('--sequence must list every bend exactly once.')
    else:
        remaining={i+1:set(o['between']) for i,o in enumerate(ends)};groups=[]
        while remaining:
            ready=[n for n in remaining if not any(n in deps for deps in remaining.values())]
            if not ready:raise ValueError('Conflicting gauge dependencies; choose different gauging ends. '+'; '.join(f'B{n} needs '+', '.join(f'B{m}' for m in sorted(remaining[n]))+' flat' for n in sorted(remaining) if remaining[n])+'. Use --side, or --formed-ok N=A+B when a flagged bend is clear of the gauging path.')
            n=min(ready);groups.append([n]);del remaining[n]
    positions={n:k for k,group in enumerate(groups) for n in group}
    if any(positions[i+1]>positions[j] for i,o in enumerate(ends) for j in o['between']):
        raise ValueError('--sequence violates a region that must remain flat for gauging.')
    return groups


def validate_common_groups(groups,bends,line_tolerance=.001):
    """Reject non-common axes; accepted groups remain tooling-trial candidates."""
    if not math.isfinite(line_tolerance) or line_tolerance<0:
        raise ValueError('Common-line tolerance must be finite and non-negative.')
    checks=[]
    for group in groups:
        master=bends[group[0]-1]
        for member in group[1:]:
            other=bends[member-1]
            d=master['d'];e=other['d'];dl=math.sqrt(sum(v*v for v in d));el=math.sqrt(sum(v*v for v in e))
            d=[v/dl for v in d];e=[v/el for v in e]
            cosine=max(-1.,min(1.,sum(x*y for x,y in zip(d,e))))
            angle=math.degrees(math.acos(abs(cosine)))
            vector=[y-x for x,y in zip(master['p'],other['p'])]
            along=sum(x*y for x,y in zip(vector,d))
            offset=math.sqrt(sum((x-along*y)**2 for x,y in zip(vector,d)))
            rotations=[master.get('angle_deg'),other.get('angle_deg')]
            if angle>.01 or offset>line_tolerance+1e-7:
                raise ValueError(f'B{group[0]}+B{member}: axes differ by {offset:.6f} mm / {angle:.6f} degrees; common-stroke tolerance not met.')
            if all(v is not None for v in rotations) and abs(rotations[0]-rotations[1])>.01:
                raise ValueError('Common operation has unequal bend rotations.')
            checks.append(dict(master=group[0],member=member,line_offset_mm=offset,axis_angle_deg=angle,
                               rotation_check='matched' if all(v is not None for v in rotations) else 'unavailable',
                               fold_sense_and_tooling='unverified'))
    return checks
