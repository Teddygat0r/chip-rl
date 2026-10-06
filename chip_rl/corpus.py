"""Private instance generation. No workload contents/seeds are agent observations.
Separate recipe from the legacy train generator; covers the entire supported input
address and tag domains, plus cold reset, exact extremes and sustained contention.
"""
import random
from .tasks import pack

def commands(c,seed,count=48):
    r=random.Random(seed);n=c.name;xs=[]
    if n=='elastic':
        xs=[r.getrandbits(c.width) for _ in range(count)]
        xs[:4]=[r.getrandbits(c.width) for _ in range(4)]
        xs += [0,(1<<c.width)-1]+[1<<i for i in range(c.width)]
    elif n in ('dot','tensor'):
        for val in (128,127,255,0,1):xs.append(pack([val]*16,8))
        for t in range(count):
            mode=(t//32)%4
            values=[r.randrange(256) for _ in range(16)]
            if mode==1:values=[r.choice((0,0,0,1,255)) for _ in range(16)]
            if mode==2:values=[r.choice((128,127,129,126)) for _ in range(16)]
            if mode==3:values=[(1<<r.randrange(8)) if i%2 else r.randrange(256) for i in range(16)]
            xs.append(pack(values,8))
    elif n=='scratchpad':
        # Read uninitialized words; prime bench has dirtied memory before reset.
        for a in (0,7,c.depth-1,255):xs.append(1|(a<<2))
        # Every word is written/read, with randomized data and explicit modulo aliases.
        for a in range(c.depth):
            v=r.getrandbits(32);lane=a%4
            xs.extend([(3|(a<<2)|(v<<10))<<(48*lane),(1|(a<<2))<<(48*lane)])
        for t in range(count):
            a=r.randrange(256)
            x=sum((1|(r.randrange(2)<<1)|((a if t%3 else r.randrange(256))<<2)|(r.getrandbits(32)<<10))<<(48*i) for i in range(4))
            xs.extend([x,x & ~sum(2<<(48*i) for i in range(4))])
        for bank in range(4):xs += [sum((1|(bank<<2))<<(48*i) for i in range(4))]*8
    elif n in ('gather','accelerator'):
        xs += [((1<<4)|(a<<16)) if n=='gather' else (3|(a<<8)) for a in (0,7,c.depth-1,255)]
        for a in range(c.depth):xs.append(int(n=='gather')|(a<<8)|(r.getrandbits(32)<<16))
        if n=='gather':
            for mask in range(16):
                for _ in range(2):xs.append((mask<<4)|sum(r.randrange(256)<<(16+8*i) for i in range(4)))
            for t in range(count):
                if t%5==0:
                    a=r.randrange(256);xs.extend([1|(a<<8)|(r.getrandbits(32)<<16),(1<<4)|(a<<16)])
                a=r.randrange(256);xs.append((r.randrange(16)<<4)|sum((a if i%2 else r.randrange(256))<<(16+8*i) for i in range(4)))
        else:
            for a in range(c.k):xs.append((a<<8)|(128<<16))
            xs.append(2)
            for t in range(count):xs.append(r.choice((1,2,2,3))|(r.randrange(256)<<8)|(r.randrange(256)<<16))
    elif n=='cache':
        # Cover every index and isolate every tag bit, not merely tags 0 and 1.
        tags=[0];tagbits=16-(4*c.depth).bit_length()+1
        for bit in range(tagbits):tags += [1<<bit,0]
        tags += [r.randrange(1<<tagbits) for _ in range(3)]
        for tag in tags:
            # All default indices appear in the first fill; later phases walk
            # independent indices plus boundary/high-index values at every tag.
            indices=list(range(c.depth)) if tag==tags[0] and not xs else list(dict.fromkeys([0,c.depth-1,r.randrange(c.depth),r.randrange(c.depth)]))
            for ix in indices:
                addr=(tag*4*c.depth+ix*4)&65535;data=r.getrandbits(32)
                xs += [addr<<8]+[addr<<8]*r.randrange(3)+[2|(data<<24),addr<<8,
                        1|(addr<<8)|((data^0xffffffff)<<24),addr<<8]
        # Unaligned address aliases and nonresident writes (no-write-allocate).
        for t in range(count):
            addr=r.randrange(65536);data=r.getrandbits(32)
            xs += [1|(addr<<8)|(data<<24),addr<<8,2|(data<<24),(addr&65532)<<8]
    elif n=='dma':
        for t in range(max(12,count//4)):
            cols=1+t%8;rows=1+(t//8)%8
            xs.append(1|(r.randrange(65536)<<8)|((cols-1)<<24)|((rows-1)<<27)|(r.randrange(65536)<<32))
            for _ in range(cols*rows):xs += [0]*r.randrange(4)+[2]
    elif n=='router':
        for t in range(count+40):
            port=(t//10)%5;ready=31 if t%11>=3 else 0
            xs.append((ready<<160)|sum((1|(port<<1)|(r.randrange(65536)<<4))<<(32*i) for i in range(5)))
    else:
        for t in range(count+32):
            xs.append(sum((1|(r.randrange(16)<<1)|(r.randrange(16)<<5)|(r.randrange(8)<<9))<<(24*i) for i in range(4)))
    used={'elastic':c.width,'dot':64,'tensor':128,'scratchpad':192,'dma':48,'router':165,'scoreboard':96,'accelerator':48,'cache':56,'gather':48}[n]
    # Reserved inputs must be ignored, not assumed permanently zero.
    return [(x&((1<<used)-1))|(r.getrandbits(512-used)<<used) for x in xs]

def schedule(c,n,seed):
    r=random.Random(seed ^ 0x319ac8);arrival=[];t=0
    for i in range(n):
        if i>=4:
            phase=(i//64)%3
            t += r.choice((0,0,0,1,2)) if phase==0 else (15 if i%16==0 else 0) if phase==1 else r.choice((3,4,8))
        arrival.append(t)
    limit=min(c.max_cycles,n*32+128)
    ready=[]
    while len(ready)<limit+80:
        ready += [0]*r.randrange(0,9)+[1]*r.randrange(8,25)
    if c.name=='elastic':ready[:32]=[0]*32
    return arrival,ready[:limit+80],limit

def dirty_command(c):
    return {'elastic':0x55,'dot':0,'tensor':0,'scratchpad':3|(7<<2)|(0xdeadbeef<<10),
            'gather':1|(7<<8)|(0xdeadbeef<<16),'accelerator':(7<<8)|(0xdeadbeef<<16),
            'cache':0,'dma':1|(5<<8)|(7<<24)|(7<<27)|(13<<32),
            'scoreboard':1|(7<<5)|(7<<9),'router':(31<<160)|sum((1|((i+9)<<4))<<(32*i) for i in range(5))}[c.name]
