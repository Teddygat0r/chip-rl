"""Trusted-engine mutation controls, distinct from permitted candidate mapper actions."""
import argparse,json
from pathlib import Path
from chip_rl.layout.spec import Shape
from chip_rl.layout.rtl import design
from chip_rl.layout.synthesis import Synthesis
from chip_rl.layout.verification import probes
from chip_rl.layout.simulation import workload,reset_cancellation
from chip_rl.evaluate import Rejected,digest
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
s=Shape(8,8,8,8);source=design();net,_=Synthesis(a.cache).compile(s,source)
import chip_rl.layout.simulation as sim
engine=Path(sim.__file__).with_name('engine.sv').read_text();rows=[]
changes=[('no_reset_clear','for(i=0;i<ROWS*COLS;i=i+1)mem[i]<=0;','',False),('ignore_write_mask','pending<=mask','pending<=write_req ? {LANES{1\'b1}} : mask',False),('fake_persistence','out_data[32*j+:32]<=mem[saved_addr[chosen]]','out_data[32*j+:32]<=saved_data[chosen]',False),('alias_storage','mem[saved_addr[chosen]]','mem[saved_addr[chosen]%8]',False),('reverse_write_order',' && chosen<0','',False),('extra_bank_ports','if(saved_write)begin mem[saved_addr[chosen]]<=saved_data[chosen];next_pending[chosen]=0;end','if(saved_write)begin for(j=0;j<LANES;j=j+1)if(pending[j] && saved_addr[j]%BANKS==b)begin mem[saved_addr[j]]<=saved_data[j];next_pending[j]=0;end end',False),('expire_stalled_response','if(out_valid && out_ready)out_valid<=0','if(out_valid)out_valid<=0',False),('hold_response_on_reset','busy<=0;out_valid<=0;out_data<=0','busy<=0;if(out_valid)out_valid<=1;else out_valid<=0;out_data<=0',True),('hold_busy_on_reset','if(rst)begin busy<=0;','if(rst)begin if(busy)busy<=1;else busy<=0;',True)]
# Positive controls exercise both direct harnesses on the same exact engine.
for cancel in (False,True):
 root=a.output/('control-cancel' if cancel else 'control-persistence')
 r=reset_cancellation(s,source,net/'netlist.v',root) if cancel else workload(s,source,net/'netlist.v',list(range(s.words)),probes(s,202020),root)
 rows.append({'case':root.name,'expected_pass':True,'passed':True,'result':r})
for name,old,new,cancel in changes:
 assert old in engine;mutated=engine.replace(old,new);root=a.output/name
 try:
  if cancel:reset_cancellation(s,source,net/'netlist.v',root,engine_source=mutated)
  else:workload(s,source,net/'netlist.v',list(range(s.words)),probes(s,202020),root,engine_source=mutated)
  passed=True;error=None
 except Rejected as e:passed=False;error=str(e);assert 'layout-simulation: exit' in error and 'FATAL:' in error,error
 row={'case':name,'expected_pass':False,'passed':passed,'error':error,'mutated_engine_sha256':digest(mutated),'scope':'trusted-host fixed-engine fault injection; not candidate action'};rows.append(row);(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(name,'REJECTED' if not passed else 'MISSED',flush=True);assert not passed,name
(a.output/'results.json').write_text(json.dumps(rows,indent=2))
