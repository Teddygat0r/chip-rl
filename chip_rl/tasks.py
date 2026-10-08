"""Trusted task contracts and independent integer reference machines.
All command fields are little-endian bit packed. See docs/contracts.md.
"""
from dataclasses import dataclass
import random

NAMES = ('elastic','dot','scratchpad','dma','router','scoreboard','tensor','accelerator','cache','gather')
def bits(x, lo, n): return (x >> lo) & ((1 << n)-1)
def signed(x): return x-256 if x & 128 else x
def pack(xs, width): return sum((v & ((1<<width)-1)) << (i*width) for i,v in enumerate(xs))

@dataclass(frozen=True)
class Config:
    name: str
    width: int = 16
    depth: int = 256
    k: int = 4
    objective: str = "balanced"
    max_cells: int = 250000
    max_cycles: int = 30000
    def __post_init__(self):
        if self.objective not in ('area','balanced','latency'):raise ValueError('unsupported objective')
        if any(type(v) is not int for v in (self.width,self.depth,self.k,self.max_cells,self.max_cycles)):
            raise ValueError('configuration values must be integers')
        if not 1<=self.max_cells<=1000000 or not 1<=self.max_cycles<=100000:
            raise ValueError('resource bounds outside supported limits')
        if self.name not in NAMES or self.width not in (8,12,16,20,24) or self.depth not in (16,32,64,128,256) or self.k not in (1,2,3,4):
            raise ValueError('unsupported task configuration')

class Model:
    def __init__(self, c):
        self.c=c; self.mem=[0]*c.depth; self.ptr=[0]*5
        self.busy=[0]*16; self.dest=[0]*4; self.tags=[None]*c.depth
        self.active=False; self.row=0; self.col=0; self.base=0
        self.pending=None
    def step(self,x):
        c=self.c; n=c.name; b=lambda lo,w:bits(x,lo,w)
        if n=='elastic': return b(0,c.width)
        if n=='dot': return sum(signed(b(i*8,8))*signed(b(32+i*8,8)) for i in range(c.k)) & ((1<<18)-1)
        if n=='tensor':
            return pack([sum(signed(b((r*4+j)*8,8))*signed(b(64+(j*2+s)*8,8)) for j in range(c.k)) for r in range(2) for s in range(2)],18)
        if n=='scratchpad':
            out=0
            for bank in range(4):
                req=[i for i in range(4) if b(i*48,1) and b(i*48+2,8)%c.depth%4==bank]
                win=next((i for off in range(4) if (i:=(self.ptr[bank]+off)%4) in req),None)
                if win is not None:
                    a=b(win*48+2,8)%c.depth; d=b(win*48+10,32)
                    if b(win*48+1,1): self.mem[a]=d
                    out |= 1<<win; out |= self.mem[a]<<(8+32*win); self.ptr[bank]=(win+1)%4
            return out
        if n=='router':
            out=0
            for port in range(5):
                if not b(160+port,1): continue
                for off in range(5):
                    i=(self.ptr[port]+off)%5
                    if b(i*32,1) and b(i*32+1,3)==port:
                        out|=1<<i; out|=1<<(8+port); out|=b(i*32+4,16)<<(16+16*port)
                        self.ptr[port]=(i+1)%5; break
            return out
        if n=='scoreboard':
            self.busy=[max(0,t-1) for t in self.busy]
            for off in range(4):
                i=(self.ptr[0]+off)%4; q=i*24; src=b(q+1,4); dst=b(q+5,4)
                if b(q,1) and not self.busy[src] and not self.busy[dst]:
                    self.busy[dst]=1+b(q+9,3); self.ptr[0]=(i+1)%4
                    return (1<<i) | (sum((t>0)<<j for j,t in enumerate(self.busy))<<8)
            return sum((t>0)<<j for j,t in enumerate(self.busy))<<8
        if n=='dma':
            if b(0,1) and not self.active:
                self.base=b(8,16); self.cols=1+b(24,3); self.rows=1+b(27,3); self.stride=b(32,16); self.row=self.col=0; self.active=True
            out=0
            if self.active:
                addr=(self.base+self.row*self.stride+4*self.col)&65535
                out=1 | (addr<<8) | ((15<<(addr%4))<<24) | ((self.row==self.rows-1 and self.col==self.cols-1)<<32)
                if b(1,1):
                    self.col+=1
                    if self.col==self.cols: self.col=0; self.row+=1
                    if self.row==self.rows: self.active=False
            return out
        if n=='accelerator':
            op=b(0,2); a=b(8,8)%c.depth
            if op==0: self.mem[a]=b(16,32); return 0
            if op==1:
                src=b(16,8)%c.depth
                # DMA one word per accepted command, overlap has sequential semantics.
                self.mem[a]=self.mem[src]; return self.mem[a]
            if op==2:
                z=b(16,8)%c.depth
                return sum(signed(self.mem[(a+i)%c.depth]&255)*signed(self.mem[(z+i)%c.depth]&255) for i in range(c.k)) & ((1<<18)-1)
            return self.mem[a]
        if n=='cache':
            op=b(0,2); addr=b(8,16)&65532; index=(addr//4)%c.depth; tag=addr//(4*c.depth); data=b(24,32)
            if op==2:
                if self.pending is None: return 0
                a=self.pending; ix=(a//4)%c.depth
                self.tags[ix]=a//(4*c.depth); self.mem[ix]=data; self.pending=None
                return 1 | (data<<8)
            if self.pending is not None: return 4
            if op==1:
                if self.tags[index]==tag: self.mem[index]=data
                return 1 | 8 | (addr<<40) | (data<<8)
            if self.tags[index]==tag: return 1 | 2 | (self.mem[index]<<8)
            self.pending=addr; return 4 | (addr<<40)
        if n=='gather':
            if b(0,1): self.mem[b(8,8)%c.depth]=b(16,32); return 0
            selected=[self.mem[b(16+i*8,8)%c.depth] for i in range(4) if b(4+i,1)]
            return len(selected) | (pack(selected,32)<<8)
        raise AssertionError(n)

def workload(c, seed=1, count=100, split='train'):
    """Directed prefix + random stream; heldout uses distinct contention/address distributions."""
    r=random.Random(seed); n=c.name; xs=[]
    if n=='cache':
        # Directly observe write-through hit updates before any eviction, then
        # test conflict refill and no-write-allocation on a nonresident line.
        xs += [0, 0, 2|(42<<24), 0, 1|(99<<24), 0,
               1024<<8, 0, 2|(88<<24), 1024<<8,
               1|(4<<8)|(77<<24), 4<<8, 2|(77<<24), 4<<8]
    if n in ('accelerator','gather'):
        for a in range(c.depth):
            data=r.getrandbits(32)
            xs.append((a<<8)|(data<<16)|(1 if n=='gather' else 0))
    for t in range(count):
        if n=='elastic': x=r.getrandbits(c.width)
        elif n in ('dot','tensor'):
            vals=[r.choice([0,1,127,128,255]) if t<20 else r.randrange(256) for _ in range(16)]
            x=pack(vals,8)
        elif n=='scratchpad':
            x=0
            for i in range(4):
                a=(t%4 if split=='heldout' or t<20 else r.randrange(c.depth))
                x |= (1 | (r.randrange(2)<<1) | (a<<2) | (r.getrandbits(32)<<10))<<(48*i)
        elif n=='router':
            x=sum((1|((t%5 if t<25 or split=='heldout' else r.randrange(5))<<1)|(r.randrange(65536)<<4))<<(32*i) for i in range(5))
            x|=(31 if t<25 else r.randrange(32))<<160
        elif n=='scoreboard':
            x=sum((1|(r.randrange(16)<<1)|(r.randrange(16)<<5)|(r.randrange(8)<<9))<<(24*i) for i in range(4))
        elif n=='dma':
            x=((t%40==0)<<0)|(r.choice([0,1,1])<<1)|(r.randrange(65536)<<8)|(r.randrange(4)<<24)|(r.randrange(3)<<27)|(r.randrange(64)<<32)
        elif n=='accelerator': x=r.choice([1,2,2,3]) | (r.randrange(c.depth)<<8) | (r.randrange(c.depth)<<16)
        elif n=='cache':
            # Refill acknowledgement after variable command ticks, then hits/conflicts/writes.
            phase=t%8; addr=((t//8)%4)*4
            op=2 if phase==3 else (1 if phase==6 else 0)
            if phase==7: addr+=4*c.depth
            x=op|(addr<<8)|(r.getrandbits(32)<<24)
        else: x=(r.randrange(16)<<4)|sum(r.randrange(c.depth)<<(16+8*i) for i in range(4))
        xs.append(x)
    return xs

def useful_work(c,x,y):
    """Units retired by this command; zero-cost control ticks are excluded."""
    if c.name=='dma': return int(bool(y&1) and bool(x&2))
    if c.name in ('scratchpad','router','scoreboard'): return bits(y,0,5 if c.name=='router' else 4).bit_count()
    if c.name=='cache': return int(bool(y&1))
    if c.name=='accelerator': return c.k if x&3==2 else 0
    if c.name=='gather': return bits(y,0,3) if not x&1 else 0
    if c.name=='tensor': return 4*c.k
    if c.name=='dot': return c.k
    return 1
