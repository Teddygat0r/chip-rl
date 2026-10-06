"""Task-specific plausible design mistakes; all remain syntactically synthesizable."""
from .rtl import design

def semantic(c):
    s=design(c);n=c.name
    if n in ('scratchpad','router'): return design(c,mutant='unfair')
    replacements={
      'elastic':(f'y[{c.width-1}:0]=in_data[{c.width-1}:0];',f'y[{c.width-2}:0]=in_data[{c.width-2}:0];'),
      'dot':('$signed','$unsigned'),
      'tensor':('$signed','$unsigned'),
      'dma':('addr=nb+nr*ns+4*nc','addr=nb+4*nc'),
      'scoreboard':('nb[in_data[i*24+1+:4]]==0',"1'b1"),
      'accelerator':('acc=acc+$signed','acc=acc-$signed'),
      'cache':('mem[ix]<=in_data[24+:32]',"mem[ix]<=32'b0"),
      'gather':('in_data[16+i*8+:8]', 'in_data[16+(3-i)*8+:8]'),
    }
    a,b=replacements[n]
    assert a in s,n
    return s.replace(a,b)
