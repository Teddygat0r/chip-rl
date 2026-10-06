"""Separate challenge generator; does not call/import training workload builders.
Published seeds are regression examples, not hidden secrets. A trusted host should
choose private seeds. It shares the specification, not training generation logic.
"""
import random

def challenge(c,seed,count=128):
    r=random.Random(seed ^ 0xC0FFEE); out=[]; n=c.name
    if n in ('gather','accelerator'):
        for a in range(c.depth):out.append((int(n=='gather'))|(a<<8)|((0x80 if a%3==0 else a*17&255)<<16))
    for t in range(count):
        if n=='elastic':out.append(((1<<(t%c.width)) if t%2 else ((1<<c.width)-1)^(1<<(t%c.width))))
        elif n in ('dot','tensor'):
            # Uniform matrices plus one-hot impulses, sign boundaries and mixed signs.
            values=[r.choice((0,1,127,128,255)) for _ in range(16)]
            if t%4==0:values=[128]*16
            if t%4==1:values=[255 if j%2 else 127 for j in range(16)]
            out.append(sum(v<<(8*j) for j,v in enumerate(values)))
        elif n=='scratchpad':
            a=(t//4)%c.depth
            # Observe each written address on the following command; vary valid masks.
            valid=15 if t%8<6 else r.randrange(16);write=(t%2==0)
            out.append(sum((((valid>>j)&1)|(int(write)<<1)|(((a if t%3 else (a+j)%c.depth))<<2)|((0x98765432^t^j)<<10))<<(48*j) for j in range(4)))
        elif n=='router':
            ready=0 if t%11<3 else (31 if t%2 else 1<<(t%5))
            out.append((ready<<160)|sum(((int((t+j)%7!=0))|(((t//9 if t%3 else j)%5)<<1)|((0x8000+t+j)<<4))<<(32*j) for j in range(5)))
        elif n=='scoreboard':
            # Sustained independent contenders, then RAW/WAW chains and idle ticks.
            if t%17==0:out.append(0);continue
            out.append(sum((1|((j if t%3 else 8+(j+3)%4)<<1)|((8+j if t%5 else 8)<<5)|(((t+j)%8)<<9))<<(24*j) for j in range(4)))
        elif n=='dma':
            # Whole descriptors, exhaustive 1..8 row/column sizes, misalignment,
            # wraparound, delayed ack and starts while busy (defined ignored).
            cols=1+t%8;rows=1+(t//8)%8;base=(65520+t)%65536;stride=3+7*t
            out.append(1|(base<<8)|((cols-1)<<24)|((rows-1)<<27)|((stride&65535)<<32))
            for beat in range(cols*rows):
                out.extend([0]*r.randrange(4));out.append(2)
        elif n=='accelerator':
            a=(c.depth-1-t)%c.depth;b=(t*7)%c.depth
            out.extend([1|(a<<8)|(b<<16),3|(a<<8),2|(a<<8)|(b<<16)])
        elif n=='cache':
            a=((t%c.depth)*4);conflict=a+4*c.depth;data=r.getrandbits(32);updated=data^0xffffffff
            # Evict/reload every index, delayed refills, hit writes with immediate
            # readback, and nonresident writes (no allocation).
            out.extend([a<<8]+[a<<8]*r.randrange(4)+[2|(data<<24),a<<8,1|(a<<8)|(updated<<24),a<<8,
                        conflict<<8,2|((t+1)<<24),conflict<<8,1|(a<<8)|(data<<24),a<<8,2|(data<<24),a<<8])
        else:
            mask=t%16;addr=[c.depth-1,0,(t*7)%c.depth,c.depth-1]
            out.append((mask<<4)|sum(a<<(16+8*j) for j,a in enumerate(addr)))
    return out
