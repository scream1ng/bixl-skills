"""Detect crossings between orthogonal feature leaders before rendering."""
def crossing(a,b,c,d):
    if a[0]==b[0]and c[0]==d[0]:
        if a[0]!=c[0]:return None
        lo=max(min(a[1],b[1]),min(c[1],d[1]));hi=min(max(a[1],b[1]),max(c[1],d[1]))
        return ('overlap',)if lo<hi else (a[0],lo)if lo==hi else None
    if a[1]==b[1]and c[1]==d[1]:
        if a[1]!=c[1]:return None
        lo=max(min(a[0],b[0]),min(c[0],d[0]));hi=min(max(a[0],b[0]),max(c[0],d[0]))
        return ('overlap',)if lo<hi else (lo,a[1])if lo==hi else None
    if a[1]==b[1]:a,b,c,d=c,d,a,b
    point=(a[0],c[1])
    return point if min(a[1],b[1])<=point[1]<=max(a[1],b[1])and min(c[0],d[0])<=point[0]<=max(c[0],d[0])else None


def validate(paths):
    for index,path in enumerate(paths):
        segments=[(a,b)for a,b in zip(path,path[1:])if a!=b]
        for i,(a,b)in enumerate(segments):
            for c,d in segments[i+2:]:
                if crossing(a,b,c,d)is not None:raise ValueError('Feature leader crosses itself; revise its elbows.')
        for other in paths[:index]:
            for a,b in segments:
                for c,d in zip(other,other[1:]):
                    if c==d:continue
                    hit=crossing(a,b,c,d)
                    if hit is not None and not(hit==tuple(path[0])==tuple(other[0])):
                        raise ValueError('Feature leaders cross or overlap; move badges or revise elbows.')
