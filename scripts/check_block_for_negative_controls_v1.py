"""Numerical negative controls; all three sources must synthesize and miscompute in RTL and mapped replay."""
import hashlib,json,os,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.block_for.rtl import design
from chip_rl.block_for.oracle import expected,pack_input
from chip_rl.block_for.synthesis import Synthesis
from chip_rl.evaluate import run,tool,TOOLS

private=Path(os.environ['CHIP_RL_FOR_PRIVATE']);out=Path(os.environ['CHIP_RL_FOR_EVIDENCE'])
manifest=json.loads((private/'predeclared.json').read_text());source=design('serial')
assert hashlib.sha256(source.encode()).hexdigest()==manifest['generated_candidates']['serial']
mutations={
 'wrong_width': [('if(delta[k])bits_needed=k+1;','if(delta[k])bits_needed=k;')],
 'signed_minmax': [('if(bytes_reg[8*index+:8]<minimum)','if($signed(bytes_reg[8*index+:8])<$signed(minimum))'),
                   ('if(bytes_reg[8*index+:8]>maximum)','if($signed(bytes_reg[8*index+:8])>$signed(maximum))')],
 'packing_position': [('<< (12+(index+i)*width)','<< (13+(index+i)*width)')],
}
TB='''module tb;
reg clk=0,rst=1,in_valid=0,out_ready=1;reg [511:0] in_data=512'hWORD;
wire in_ready,out_valid;wire [255:0] out_data;
candidate INSTANTIATION dut(.*);
integer t=0,accepted=0,observed=0;
initial begin
 #2;clk=1;#2;clk=0;rst=0;
 while(t<200 && observed==0)begin
  in_valid=accepted==0;#1;
  if(in_valid && in_ready)accepted=1;
  if(out_valid)begin
   if(accepted!=1 || (^out_data)===1'bx)$fatal(1,"unknown/unsolicited result");
   $display("OBSERVED %064h",out_data);observed=1;
  end
  clk=1;#2;clk=0;#1;t=t+1;
 end
 if(accepted!=1 || observed!=1)$fatal(1,"timeout");
 $finish;
end endmodule'''
synth=Synthesis(private/'mutant-cache');rows=[]
for label,edits in mutations.items():
 mutant=source
 for old,new in edits:
  assert mutant.count(old)==1,(label,old,mutant.count(old));mutant=mutant.replace(old,new)
 assert mutant!=source
 witness=manifest['witnesses'][label];want=expected(pack_input(witness),4)
 build,struct=synth.compile(4,mutant)
 d=private/'negative-controls'/label;d.mkdir(parents=True,exist_ok=False)
 (d/'candidate.sv').write_text(mutant)
 (d/'netlist.v').write_bytes((build/'netlist.v').read_bytes())
 results={}
 for stage,file in (('rtl','candidate.sv'),('mapped','netlist.v')):
  template=TB.replace('WORD',f'{pack_input(witness):0128x}').replace('INSTANTIATION','#(.N(4))' if stage=='rtl' else '')
  (d/(stage+'-tb.sv')).write_text(template)
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  run(cmd+['-g2012','-s','tb','-o',stage+'.vvp',file,stage+'-tb.sv'],d,label+'-'+stage+'-compile',45)
  log=run([tool('vvp'),stage+'.vvp'],d,label+'-'+stage+'-simulation',90)
  m=re.search(r'^OBSERVED ([0-9a-f]{64})$',log,re.M)
  assert m,log
  got=int(m[1],16)
  assert got!=want,(label,stage,'mutant unexpectedly matched oracle')
  results[stage]=got
 assert results['rtl']==results['mapped'],label
 row={'mutant':label,'witness':witness,'expected_hex':f'{want:064x}',
      'rtl_hex':f"{results['rtl']:064x}",'mapped_hex':f"{results['mapped']:064x}",
      'mutant_sha256':hashlib.sha256(mutant.encode()).hexdigest(),'cells':struct['cells'],
      'compiled_and_synthesized':True,'rtl_numerical_mismatch':True,'mapped_numerical_mismatch':True}
 rows.append(row);print(json.dumps(row),flush=True)
(out/'negative-controls.json').write_text(json.dumps(rows,indent=2)+'\n')
