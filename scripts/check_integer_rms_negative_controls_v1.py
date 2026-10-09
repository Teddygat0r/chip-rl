"""Phase-2 host-only mutant detections; never changes family source/oracle."""
from pathlib import Path
import json,hashlib,os
from chip_rl.integer_rms.rtl import design
from chip_rl.integer_rms.oracle import pack,expected
from chip_rl.integer_rms.synthesis import Synthesis
from chip_rl.integer_rms.arithmetic_check import TB
from chip_rl.evaluate import Rejected,run,tool,TOOLS,sanitize,digest
base=Path(__file__).resolve().parents[2]
source=design('serial');freeze=json.loads((base/'integer-rms-phase2-freeze.json').read_text())
assert digest(source)==freeze['reference_source_sha256']['serial']
controls=(
 ('omit_epsilon',"wire [31:0] mean_plus_one=(sum/N)+35'd1;","wire [31:0] mean_plus_one=(sum/N);",(2,2,2,0)),
 ('narrow_abs',"magnitude16=sx[16] ? -sx : sx;","magnitude16=sx[16] ? (-sx & 17'h07fff) : sx;",(-32768,0,0,0)),
 ('truncate_ties',"if(twice>{1'b0,divisor} || (twice=={1'b0,divisor} && q[0]))q=q+1'b1;","if(1'b0)q=q+1'b1;",(1024,3,0,0)),
)
s=Synthesis(base/'smoke-cache');results=[]
for name,old,new,lanes in controls:
 assert source.count(old)==1,name
 mutant=source.replace(old,new)
 assert mutant!=source and digest(mutant)!=digest(source)
 sanitize(mutant)
 dest=base/'integer-rms-phase2-negative-controls'/name;dest.mkdir(parents=True,exist_ok=True)
 (dest/'candidate.sv').write_text(mutant)
 build,struct=s.compile(4,mutant)
 (dest/'netlist.v').write_bytes((build/'netlist.v').read_bytes())
 word=pack(lanes);oracle=expected(word,4)
 (dest/'inputs.hex').write_text(f'{word:0128x}\n')
 (dest/'expected.hex').write_text(f'{oracle:064x}\n')
 template=TB.replace('COUNT','1').replace('LIMIT','256')
 stages={}
 for stage,file in (('rtl','candidate.sv'),('mapped','netlist.v')):
  (dest/(stage+'-tb.sv')).write_text(template.replace('INSTANTIATION','#(.N(4))' if stage=='rtl' else ''))
  cmd=[tool('iverilog')]
  if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
  try:
   run(cmd+['-g2012','-s','tb','-o',stage+'.vvp',file,stage+'-tb.sv'],dest,name+'-'+stage+'-compile',45)
   compile_ok=True
  except Rejected as e:
   stages[stage]={'screened':True,'compiled':False,'numerically_detected':False,'error':str(e)};continue
  try:
   log=run([tool('vvp'),stage+'.vvp'],dest,name+'-'+stage+'-simulation',90)
   stages[stage]={'screened':True,'compiled':True,'numerically_detected':False,'log_tail':log[-400:]}
  except Rejected as e:
   log=(dest/(name+'-'+stage+'-simulation.log')).read_text()
   stages[stage]={'screened':True,'compiled':True,'numerically_detected':'arithmetic mismatch' in log,'log_tail':log[-400:]}
 row={'mutation':name,'mutant_source_sha256':digest(mutant),'witness_lanes':lanes,'oracle_output_hex':f'{oracle:064x}','cells':struct['cells'],'stages':stages}
 (dest/'summary.json').write_text(json.dumps(row,indent=2)+'\n');results.append(row)
 print(name,{k:(v['compiled'],v['numerically_detected']) for k,v in stages.items()},flush=True)
assert digest(design('serial'))==freeze['reference_source_sha256']['serial']
(base/'integer-rms-phase2-negative-controls'/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
