"""Bounded transaction proof, separate from cycle-exact equivalence.
This is BMC (12 cycles), never labelled an unbounded proof.
"""
import json, shutil, tempfile
from pathlib import Path
from .evaluate import run, tool, sanitize, Rejected

def check_elastic(source,width=8,depth=12,artifacts=None):
    result={'status':'unproven','kind':'bounded_transaction_safety','bound':depth,'width':width}
    with tempfile.TemporaryDirectory(prefix='chip-formal-') as td:
        d=Path(td)
        try:
            sanitize(source);(d/'candidate.sv').write_text(source)
            (d/'formal.sv').write_text(f'''module formal_top(input clk,input in_valid,input out_ready,input [511:0] in_data);
              reg rst=1; always @(posedge clk) rst<=0;
              wire in_ready,out_valid; wire [255:0] out_data;
              candidate dut(.*);
              reg [{width-1}:0] queue[0:15]; reg [4:0] used=0; integer i;
              wire push=in_valid && in_ready; wire pop=out_valid && out_ready;
              reg stalled=0;reg [255:0] held=0;
              always @(posedge clk) begin
                if(rst) begin used<=0;stalled<=0;end
                else begin
                  assert(used<=16);
                  if(out_valid) begin assert(used>0);assert(out_data==queue[0]);end
                  if(stalled) begin assert(out_valid);assert(out_data==held);end
                  stalled<=out_valid && !out_ready;held<=out_data;
                  if(pop) for(i=0;i<15;i=i+1) queue[i]<=queue[i+1];
                  if(push) queue[used-pop]<=in_data[{width-1}:0];
                  used<=used+push-pop;
                end
              end
            endmodule''')
            script=f'read_verilog -formal -sv candidate.sv formal.sv; prep -top formal_top -flatten; memory_map; opt; async2sync; chformal -lower; sat -seq {depth} -set-init-zero -prove-asserts -verify -timeout 45'
            (d/'formal.ys').write_text(script)
            out=run([tool('yosys'),'-s','formal.ys'],d,'formal',60)
            if 'SUCCESS!' not in out: raise Rejected('no proof success marker')
            result['status']='bounded_pass'
        except (Rejected,OSError) as e: result['error']=str(e)
        (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if artifacts: shutil.copytree(d,artifacts)
    return result

def check_cycle_equivalence(gold,gate,depth=12,artifacts=None):
    """Compare all ports cycle-by-cycle, including idle data. Not a transaction test.
    Only for explicitly fixed-cycle specifications; BMC is bounded evidence.
    """
    import re
    result={'status':'unproven','kind':'bounded_fixed_cycle_equivalence','bound':depth}
    with tempfile.TemporaryDirectory(prefix='chip-equiv-') as td:
        d=Path(td)
        try:
            for label,source in [('gold',gold),('gate',gate)]:
                sanitize(source)
                (d/(label+'.sv')).write_text(re.sub(r'\bmodule candidate\b','module '+label,source))
            script=f'''read_verilog -sv gold.sv gate.sv
            proc
            miter -equiv -make_assert -flatten gold gate miter
            hierarchy -top miter
            proc; flatten; memory_map; opt; async2sync; chformal -lower
            sat -seq {depth} -set-init-zero -set in_rst 0 -set-at 1 in_rst 1 -prove-asserts -verify -timeout 45'''
            (d/'equiv.ys').write_text(script);text=run([tool('yosys'),'-s','equiv.ys'],d,'equivalence',60)
            if 'SUCCESS!' not in text: raise Rejected('no proof success marker')
            result['status']='bounded_pass'
        except (Rejected,OSError) as e: result['error']=str(e)
        (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if artifacts: shutil.copytree(d,artifacts)
    return result
