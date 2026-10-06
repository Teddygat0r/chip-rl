"""Regression exploits discovered in the v1 viability audit (never valid actions)."""
from .rtl import design
from .tasks import Config,Model
from .corpus import commands

def mutant(c,label):
    s=design(c)
    if label=='padding':return s.replace('data[0]<=y;',"data[0]<=y ^ ({255'b0,in_data[511]}<<255);")
    if label=='ignore_late_writes':
        s=s.replace('integer st;', 'integer st;reg [15:0] accepted_count;').replace('valid<=0;','valid<=0;accepted_count<=0;').replace('if(fire) begin ', 'if(fire) begin accepted_count<=accepted_count+1; ')
        if c.name=='scratchpad':return s.replace('if(in_data[win[z]*48+1]) mem[','if(in_data[win[z]*48+1] && accepted_count<2*DEPTH+4) mem[')
        if c.name=='gather':return s.replace('if(in_data[0]) mem[','if(in_data[0] && accepted_count<DEPTH+4) mem[')
        raise ValueError('memory family required')
    if label=='zero':return s.replace('data[0]<=y;',"data[0]<=256'b0;")
    if label=='duplicate':return s.replace('valid[0]<=in_valid;', 'valid[0]<=in_valid || valid[0];')
    if label=='late_drop':
        s=s.replace('integer st;', 'integer st;reg [15:0] accepted_count;').replace('valid<=0;','valid<=0;accepted_count<=0;')
        s=s.replace('if(fire) begin ', 'if(fire) begin accepted_count<=accepted_count+1; ')
        return s.replace('valid[0]<=in_valid;', 'valid[0]<=in_valid && accepted_count<64;')
    if label=='no_reset':return s.replace('mem[z]<=0;', 'mem[z]<=mem[z];')
    if label=='cache_reset':return s.replace('cvalid<=0;', 'cvalid<=cvalid;')
    if label=='gather_order':return s.replace('in_data[16+i*8+:8]', 'in_data[16+(3-i)*8+:8]')
    if label=='narrow':return s.replace('reg signed [17:0] acc;', 'reg signed [15:0] acc;')
    if label=='unfair':return design(c,mutant='unfair')
    if label=='negedge':return s.replace('posedge clk','negedge clk')
    if label=='hardcode':
        # Leaves declared parameters but ignores the overridable dimension.
        key={'elastic':'WIDTH','dot':'K','tensor':'K','scratchpad':'DEPTH','cache':'DEPTH','gather':'DEPTH'}[c.name]
        i=s.index(')(')+2
        return s[:i]+s[i:].replace(key,str(getattr(c,{'WIDTH':'width','K':'k','DEPTH':'depth'}[key])))
    if label=='tag_alias':return s.replace('tg=addr/(4*DEPTH);','tg=(addr/(4*DEPTH))%2;').replace('tag[pi]<=pa/(4*DEPTH);','tag[pi]<=(pa/(4*DEPTH))%2;')
    if label=='divergence':
        return s.replace('if(in_valid) data[0]<=y;',"if(in_valid) begin case(1'bx) 1'b0:data[0]<=0;1'b1:data[0]<=1;default:data[0]<=y;endcase end")
    if label=='capacity':return design(c,1)
    if label=='bypass':
        a=s.index('    localparam S=');b=s.index('    reg [255:0] y; integer st;')
        s=s[:a]+'''assign in_ready=out_ready && !rst;
        assign out_valid=in_valid && !rst;assign out_data=y;
        wire fire=in_valid && in_ready;
'''+s[b:]
        s=s.replace('        valid<=0;\n        for(st=0;st<S;st=st+1) data[st]<=0;','')
        a=s.index('        for(st=S-1;');b=s.index('        if(fire)',a)
        return s[:a]+s[b:]
    if label=='rom':
        # Knows the generator and a public development seed, never private instances.
        m=Model(c);ys=[m.step(x) for x in commands(c,71,48)[:128]]
        out=design(Config('elastic'),4 if c.name=='elastic' else 1)
        out=out.replace('integer st;', 'integer st;reg [15:0] idx;')
        table='case(idx)\n'+'\n'.join(f"{i}:y=256'h{v:064x};" for i,v in enumerate(ys))+'\ndefault:y=0;endcase'
        return out.replace('y[(WIDTH-1):0]=in_data[(WIDTH-1):0];',table).replace('valid<=0;','valid<=0;idx<=0;').replace('if(fire) begin  end','if(fire) begin idx<=idx+1; end')
    raise ValueError(label)

def labels(name):
    result=['padding','zero','duplicate','bypass','hardcode','rom','negedge','divergence','late_drop']
    if name in ('scratchpad','gather'):result+=['no_reset','ignore_late_writes']
    if name=='scratchpad':result+=['unfair']
    if name in ('dot','tensor'):result+=['narrow']
    if name=='elastic':result+=['capacity']
    if name=='cache':result+=['tag_alias','cache_reset']
    if name=='gather':result+=['gather_order']
    return result

def threshold_mutant(c,threshold):
    if type(threshold) is not int or not 1<=threshold<=65534:raise ValueError('threshold')
    return mutant(c,'late_drop').replace('accepted_count<64',f'accepted_count<{threshold}')
