"""Experimental cycle-exact evaluator. Every passing result runs RTL AND netlist."""
import json,secrets,tempfile,re,hashlib,time
from pathlib import Path
from dataclasses import replace,asdict
from ..evaluate import TrustedEvaluator,tool,TOOLS,run,Rejected,digest
from .traffic import trace
from .rtl import design

def simulate(q,c,src,sd,seed,out=None):
 rows,stats=trace(c,seed,live=512+seed%257)
 with tempfile.TemporaryDirectory(prefix='chip-cycle-') as td:
  d=Path(td);(d/'candidate.sv').write_text(src);(d/'netlist.v').write_text((sd/'netlist.v').read_text())
  (d/'vectors.hex').write_text(''.join(f'{(rst|(v<<1)|(x<<2)|(y<<514)):0193x}\n' for rst,v,x,y in rows))
  tb=f'''module tb;reg clk=0,rst=1,in_valid=0,out_ready=1;reg [511:0] in_data=0;wire in_ready,out_valid;wire [255:0] out_data;
  candidate #(.WIDTH({c.width}),.DEPTH({c.depth}),.K({c.k})) dut(.*);
  reg [769:0] vec[0:{len(rows)-1}];integer i;
  initial begin $readmemh("vectors.hex",vec);
   for(i=0;i<{len(rows)};i=i+1)begin rst=vec[i][0];in_valid=vec[i][1];in_data=vec[i][513:2];#4;
    if(!rst && (in_ready!==1 || out_valid!==1 || out_data!==vec[i][769:514]))$fatal(1,"cycle mismatch %0d",i);
    #1;clk=1;#5;clk=0;
   end $display("PASS {len(rows)}");$finish;end endmodule'''
  try:
   for label,file in [('rtl','candidate.sv'),('netlist','netlist.v')]:
    (d/'tb.sv').write_text(tb if label=='rtl' else re.sub(r'candidate #\(.*?\)\) dut','candidate dut',tb))
    cmd=[tool('iverilog')]
    if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
    run(cmd+['-g2012','-s','tb','-o',label+'.vvp',file,'tb.sv'],d,label+'-compile')
    log=run([tool('vvp'),label+'.vvp'],d,label+'-simulation',120)
    if f'PASS {len(rows)}' not in log:raise Rejected('incomplete cycle simulation')
  finally:
   if out:
    import shutil
    Path(out).parent.mkdir(parents=True,exist_ok=True);shutil.copytree(d,out)
    (Path(out)/'private-case.json').write_text(json.dumps({'seed':seed,'config':asdict(c),'stats':stats})+'\n')
 return stats

class CycleEvaluator:
 def __init__(self,cache=None):self.q=TrustedEvaluator(cache)
 def evaluate(self,c,src,*,replay_seed=None,artifacts=None):
  if artifacts:Path(artifacts).mkdir(parents=True,exist_ok=True);Path(artifacts).chmod(0o700)
  start=time.monotonic();r={'tested_correct':False,'reward':0.,'family':c.name,'status':'experimental_cycle_controller','objective':'fixed_cycle_area','contract':digest('experimental-fixed-cycle-v1:'+json.dumps(asdict(c),sort_keys=True)),'pilot_eligible':False,'formal':'not_run','physical':'not_run','os_isolation':'not_provided','source_sha256':digest(src) if isinstance(src,str) else None}
  r['tool_fingerprint']=self.q.tool_fingerprint
  r['recipe_sha256']=digest(self.q.recipe_fingerprint+''.join(Path(__file__).with_name(n).read_text() for n in ('evaluate.py','models.py','traffic.py','rtl.py')))
  details=[]
  try:
   if c.name not in ('dma','router','scoreboard','accelerator'):raise Rejected('not a cycle task')
   if c.name=='router' and c.width not in (8,16):raise Rejected('router payload width must be 8 or 16')
   seed=secrets.randbits(128) if replay_seed is None else replay_seed
   if type(seed) is not int or not 0<=seed<2**128:raise Rejected('invalid seed')
   variants=({'dma':[replace(c,depth=16),replace(c,depth=64)],
              'router':[replace(c,width=16),replace(c,width=8)],
              'scoreboard':[replace(c,k=4),replace(c,k=2)],
              'accelerator':[replace(c,depth=16,k=4),replace(c,depth=64,k=4),replace(c,depth=16,k=2)]})[c.name]
   variants=list({(cc.width,cc.depth,cc.k):cc for cc in [c]+variants}.values())
   for index,cc in enumerate(variants):
    sd,sm,_=self.q._synth(cc,src);base=design(cc);bd,bm,_=self.q._synth(cc,base)
    for repeat in range(2):
     secret=int.from_bytes(hashlib.sha256(f'{seed}:{index}:{repeat}'.encode()).digest()[:16],'big')
     path=Path(artifacts)/f'case-{index}-{repeat}' if artifacts else None
     stats=simulate(self.q,cc,src,sd,secret,path/'candidate' if path else None)
     bs=simulate(self.q,cc,base,bd,secret,path/'baseline' if path else None)
     assert stats==bs
     details.append({'config':asdict(cc),'stats':{k:v for k,v in stats.items() if k!='fair_grants'},'cells':sm['cells'],'baseline_cells':bm['cells'],'depth':sm['logic_depth'],'baseline_depth':bm['logic_depth']})
   r.update(tested_correct=True,validation='cycle_exact_rtl_and_netlist',cases_checked=len(details),resource_metrics=details,
            reward=sum(1-.5*__import__('math').tanh(.8*__import__('math').log(x['cells']/x['baseline_cells'])) for x in details)/len(details),
            metric_scope='fixed protocol cycles; reward reflects generic-cell area only, not timing/power')
  except (Rejected,ValueError,OSError,AssertionError) as e:
   r['validation']='rejected';r['reason']='cycle qualification failed'
   if artifacts:Path(artifacts).mkdir(parents=True,exist_ok=True);(Path(artifacts)/'private-error.txt').write_text(str(e))
  r['elapsed_s']=round(time.monotonic()-start,3)
  if artifacts:Path(artifacts).mkdir(parents=True,exist_ok=True);(Path(artifacts)/'result.json').write_text(json.dumps(r,indent=2)+'\n')
  return r
