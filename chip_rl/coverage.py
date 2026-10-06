"""Mandatory coverage for every qualification entry point; no quick public profile."""
import hashlib
from dataclasses import replace
PROFILE='mandatory-variable-stream-v3'
BANDS={'target_short':(128,256),'target_long':(1024,1280),'structural':(512,768)}
def cases(c,seed,minimum_count=None):
    # Legacy host count requests may increase coverage, never reduce these floors.
    if minimum_count is not None and (type(minimum_count) is not int or not 16<=minimum_count<=2048):
        raise ValueError('invalid workload size')
    variants=[c]
    if c.name=='elastic':variants += [replace(c,width=w) for w in (8,16,24) if w!=c.width]
    elif c.name in ('dot','tensor'):variants += [replace(c,k=k) for k in (2,4) if k!=c.k]
    elif c.name in ('scratchpad','cache','gather','accelerator'):variants += [replace(c,depth=d) for d in (16,64,256) if d!=c.depth]
    result=[]
    for vi,cc in enumerate(variants):
        for repeat in range(2 if vi==0 else 1):
            secret=int.from_bytes(hashlib.sha256(f'{seed}:{vi}:{repeat}'.encode()).digest()[:16],'big')
            band=('target_short' if repeat==0 else 'target_long') if vi==0 else 'structural'
            lo,hi=BANDS[band]
            count=max(minimum_count or 0,lo+int.from_bytes(hashlib.sha256(f'length:{secret}'.encode()).digest()[:8],'big')%(hi-lo+1))
            result.append((vi,repeat,cc,secret,count,band))
    return result
