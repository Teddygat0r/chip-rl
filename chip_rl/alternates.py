"""Task-specific alternatives, not just a different shared buffer depth.
The implementations preserve the exact task contracts, including RR ordering.
"""
from .rtl import design

STRATEGIES = {
 'elastic':'globally stalled shift pipeline instead of per-stage elastic enables',
 'dot':'explicit balanced product reduction instead of loop-carried accumulation',
 'scratchpad':'reverse overwrite priority encoder instead of forward first-match encoder',
 'dma':'incremental current/row-base addresses instead of row-times-stride multiplication',
 'router':'reverse overwrite destination arbitration instead of forward first-match',
 'scoreboard':'reverse overwrite ready-context selection instead of forward first-match',
 'tensor':'four separately unrolled balanced reductions instead of nested accumulation loops',
 'accelerator':'balanced scratchpad-product reduction instead of loop-carried accumulation',
 'cache':'one-hot decoded tag/data access instead of dynamic indexed read/write ports',
 'gather':'parallel prefix-popcount destinations instead of a running compaction counter',
}

def balanced(terms):
    if len(terms)==1:return terms[0]
    mid=len(terms)//2
    return '('+balanced(terms[:mid])+' + '+balanced(terms[mid:])+')'

def alternate(c,stages=2):
    s=design(c,stages);n=c.name
    def change(old,new):
        nonlocal s
        if old not in s:raise AssertionError((n,old))
        s=s.replace(old,new)
    if n=='elastic':
        change('assign ready[g]=!valid[g] || ready[g+1];','assign ready[g]=!valid[S-1] || out_ready;')
    elif n=='dot':
        terms=[f'($signed(in_data[{8*j}+:8])*$signed(in_data[{32+8*j}+:8]))' for j in range(c.k)]
        change(f'acc=0; for(j=0;j<{c.k};j=j+1) acc=acc+$signed(in_data[j*8+:8])*$signed(in_data[32+j*8+:8]); y[17:0]=acc;', 'acc='+balanced(terms)+'; y[17:0]=acc;')
    elif n in ('scratchpad','router','scoreboard'):
        size=5 if n=='router' else 4
        change(f'for(o=0;o<{size};o=o+1)',f'for(o={size-1};o>=0;o=o-1)')
        term={'scratchpad':'win[b]<0 && ','router':'win[p]<0 && ','scoreboard':'win<0 && '}[n]
        change(term,'')
    elif n=='dma':
        change('reg active,na;', 'reg [15:0] current_addr,row_base,next_addr,next_row_base; reg active,na;')
        change('addr=0;', 'addr=0; next_addr=current_addr; next_row_base=row_base;')
        change('nr=0; nc=0;', 'nr=0; nc=0; next_addr=nb; next_row_base=nb;')
        change('addr=nb+nr*ns+4*nc;', 'addr=next_addr;')
        change('nc=nc+1; if(nc==ncs) begin nc=0; nr=nr+1; end',
               'nc=nc+1; next_addr=next_addr+4; if(nc==ncs) begin nc=0; nr=nr+1; next_row_base=next_row_base+ns; next_addr=next_row_base; end')
        change('active<=0;', 'current_addr<=0; row_base<=0; active<=0;')
        change('active<=na;', 'current_addr<=next_addr; row_base<=next_row_base; active<=na;')
    elif n=='tensor':
        start=s.index('for(r=0;r<2;r=r+1)');end=s.index('\n    end',start)
        assignments=[]
        for r in range(2):
            for col in range(2):
                terms=[f'($signed(in_data[{8*(r*4+j)}+:8])*$signed(in_data[{64+8*(j*2+col)}+:8]))' for j in range(c.k)]
                assignments.append(f'y[{18*(2*r+col)}+:18]='+balanced(terms)+';')
        s=s[:start]+'\n'.join(assignments)+s[end:]
    elif n=='accelerator':
        terms=[f'($signed(mem[(a+{j})%{c.depth}][7:0])*$signed(mem[(b+{j})%{c.depth}][7:0]))' for j in range(c.k)]
        change(f'for(j=0;j<{c.k};j=j+1) acc=acc+$signed(mem[(a+j)%{c.depth}][7:0])*$signed(mem[(b+j)%{c.depth}][7:0]);', 'acc='+balanced(terms)+';')
    elif n=='cache':
        change('integer ix,pi,z;', 'integer ix,pi,z,q; reg hit; reg [31:0] hit_data;')
        change(f'tg=addr/{4*c.depth};', f'tg=addr/{4*c.depth}; hit=0; hit_data=0; for(q=0;q<{c.depth};q=q+1) if(ix==q && cvalid[q] && tag[q]==tg) begin hit=1; hit_data=mem[q]; end')
        # Only the combinational read becomes an OR/decoded mux. Sequential writes
        # use decoded enables; there is no indexed read hidden in the alternative.
        change('y[8+:32]=mem[ix];','y[8+:32]=hit_data;')
        change('cvalid[ix] && tag[ix]==tg','hit')
        change(f'mem[pi]<=in_data[24+:32]; tag[pi]<=pa/{4*c.depth}; cvalid[pi]<=1;',f'for(z=0;z<{c.depth};z=z+1) if(pi==z) begin mem[z]<=in_data[24+:32]; tag[z]<=pa/{4*c.depth}; cvalid[z]<=1; end')
        change('mem[ix]<=in_data[24+:32];',f'for(z=0;z<{c.depth};z=z+1) if(ix==z) mem[z]<=in_data[24+:32];')
    elif n=='gather':
        start=s.index('cnt=0; if(!in_data[0])');end=s.index('\n    end',start)
        calc=['if(!in_data[0]) begin']
        for i in range(4):
            prefix=' + '.join("{2'b0,in_data[%d]}"%(4+j) for j in range(i)) or '0'
            calc.append(f'if(in_data[{4+i}]) y[8+({prefix})*32+:32]=mem[in_data[{16+i*8}+:8]%{c.depth}];')
        calc.append("y[2:0]="+' + '.join("{2'b0,in_data[%d]}"%(4+j) for j in range(4))+'; end')
        s=s[:start]+'\n'.join(calc)+s[end:]
    return s
