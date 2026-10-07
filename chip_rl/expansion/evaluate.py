"""Mandatory private paired RTL/netlist checks. No agent-selected quick mode."""
from ..audit import journal
from pathlib import Path
from dataclasses import asdict
import secrets,hashlib,json,tempfile,shutil,re,time,math
from ..evaluate import TrustedEvaluator,Rejected,run,tool,TOOLS,digest,bench
from ..tasks import Config as LegacyConfig
from ..objectives import scores,ratios,relation
from .spec import cases,identity,specification
from .models import machine
from .traffic import commands,trace
from .rtl import design

def simulate(c,src,netlist,seed,count,out=None):
 with tempfile.TemporaryDirectory(prefix='chip-expansion-') as td:
  d=Path(td);(d/'candidate.sv').write_text(src);(d/'netlist.v').write_text(netlist.read_text());stats={}
  if c.name=='retire':
   rows,stats=trace(c,seed,count)
   if len(rows)>c.max_cycles:raise Rejected('cycle budget')
   (d/'vectors.hex').write_text(''.join(f'{rst|(v<<1)|(x<<2)|(y<<514):0193x}\n' for rst,v,x,y in rows))
   tb=f'''module tb;reg clk=0,rst=1,in_valid=0,out_ready=1;reg [511:0] in_data=0;wire in_ready,out_valid;wire [255:0] out_data;
   candidate #(.WIDTH({c.width}),.DEPTH({c.depth}),.K({c.k})) dut(.*);
   reg [769:0] vec[0:{len(rows)-1}];integer i;
   initial begin $readmemh("vectors.hex",vec);for(i=0;i<{len(rows)};i=i+1)begin rst=vec[i][0];in_valid=vec[i][1];in_data=vec[i][513:2];#4;
   if(in_ready!==!rst || out_valid!==!rst || (!rst && out_data!==vec[i][769:514]))$fatal(1,"cycle mismatch %0d",i);
   #1;clk=1;#5;clk=0;end $display("PASS {len(rows)} 1 1 1 1");$finish;end endmodule'''
  else:
   xs=commands(c,seed,count);model=machine(c);ys=[model.step(x) for x in xs]
   # Reuse the generic transaction harness only; its dirty preamble is stateless.
   carrier=LegacyConfig('dot',width=16,depth=16,k=c.k,max_cycles=c.max_cycles)
   tb,arrivals,ready=bench(carrier,xs,seed)
   tb=tb.replace('.WIDTH(16),.DEPTH(16)',f'.WIDTH({c.width}),.DEPTH({c.depth})')
   weights=[work(c,x,y) for x,y in zip(xs,ys)]
   if c.name in ('crc','freelist','histogram'):
    dirty=(1<<32)|0xdeadbeef if c.name=='crc' else (1<<32)|(3<<48) if c.name=='histogram' else c.k
    tb=tb.replace("in_data=512'h0;out_ready=1;",f"in_data=512'h{dirty:x};out_ready=1;")
   for name,values,width in [('inputs',xs,128),('expected',ys,64),('release',arrivals,8),('weights',weights,8),('ready',ready,1)]:
    (d/(name+'.hex')).write_text(''.join(f'{v:0{width}x}\n' for v in values))
  answers=[]
  try:
   for label,file in [('rtl','candidate.sv'),('netlist','netlist.v')]:
    (d/'tb.sv').write_text(tb if label=='rtl' else re.sub(r'candidate #\(.*?\)\) dut','candidate dut',tb))
    cmd=[tool('iverilog')]
    if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
    run(cmd+['-g2012','-s','tb','-o',label+'.vvp',file,'tb.sv'],d,label+'-compile')
    log=run([tool('vvp'),label+'.vvp'],d,label+'-simulation',120)
    match=re.search(r'^PASS (\d+) (\d+) (\d+) (\d+) (\d+)$',log,re.M)
    if not match:raise Rejected('incomplete simulation')
    answers.append(tuple(map(int,match.groups())))
   if answers[0]!=answers[1]:raise Rejected('RTL/netlist divergence')
   n,cycles,units,lat,mx=answers[0]
   return stats if c.name=='retire' else dict(commands=n,cycles=cycles,useful_units=units,offered_latency=lat/units,useful_throughput=units/cycles,maximum_response_cycles=mx)
  finally:
   if out:
    Path(out).parent.mkdir(parents=True,exist_ok=True);shutil.copytree(d,out)
    (Path(out)/'private-case.json').write_text(json.dumps(dict(config=asdict(c),seed=seed,count=count,stats=stats))+'\n')
def bits_mask(c,x):return (x>>(152 if c.name=='permute' else 128))&((1<<c.lanes)-1)

class Evaluator:
 def __init__(self,cache=None):self.q=TrustedEvaluator(cache)
 @journal
 def evaluate(self,c,src,*,replay_seed=None,artifacts=None):
  start=time.monotonic();rows=[];reset_checked=set();r={**specification(c),'contract':identity(c),'tested_correct':False,'reward':0.,'source_sha256':digest(src) if isinstance(src,str) else None,'tool_fingerprint':self.q.tool_fingerprint}
  r['recipe_sha256']=digest(self.q.recipe_fingerprint+''.join(p.read_text() for folder in (Path(__file__).parent,Path(__file__).parent.parent/'qualification',Path(__file__).parent.parent/'history') for p in sorted(folder.glob('*.py'))))
  if artifacts:Path(artifacts).mkdir(parents=True,exist_ok=True);Path(artifacts).chmod(0o700)
  try:
   seed=secrets.randbits(128) if replay_seed is None else replay_seed
   if type(seed) is not int or not 0<=seed<2**128:raise Rejected('trusted seed')
   for i,j,cc,s,count in cases(c,seed):
    sd,sm,_=self.q._synth(cc,src);base=design(cc);bd,bm,_=self.q._synth(cc,base)
    path=Path(artifacts)/f'case-{i}-{j}' if artifacts else None
    dimensions=(cc.width,cc.depth,cc.k)
    if c.name in ('ecc','coalesce','histogram') and dimensions not in reset_checked:
     from ..qualification.workloads import reset_epochs
     from ..qualification.harness import check
     with tempfile.TemporaryDirectory(prefix='chip-reset-') as probe_temp:
      probe_path=path/'reset-probe' if path else Path(probe_temp)/'probe'
      probe=check(cc,src,reset_epochs(cc,s),probe_path,self.q.root)
      if not probe['tested_correct']:raise Rejected('mandatory reset probe: '+probe.get('error','failed'))
     reset_checked.add(dimensions)
    cm=simulate(cc,src,sd/'netlist.v',s,count,path/'candidate' if path else None)
    bm_run=simulate(cc,base,bd/'netlist.v',s,count,path/'baseline' if path else None)
    rows.append(dict(target=i==0,config=asdict(cc),candidate={**cm,'cells':sm['cells'],'logic_depth':sm['logic_depth']},baseline={**bm_run,'cells':bm['cells'],'logic_depth':bm['logic_depth']}))
   if c.name in ('crc','retire'):
    from ..history.evaluate import check as history_check
    with tempfile.TemporaryDirectory(prefix='chip-history-') as history_temp:
     history_path=Path(artifacts)/'long-history' if artifacts else Path(history_temp)/'case'
     long_result=history_check(c,src,seed^0x4c4f4e47,history_path,self.q.root)
     r['long_history']=long_result
     if not long_result['tested_correct']:raise Rejected('mandatory long history: '+long_result.get('error','failed'))
   r.update(tested_correct=True,validation='rtl_and_netlist_pass',cases_checked=len(rows),metrics=rows)
   if c.name=='retire':
    r['reward']=sum(1-.5*math.tanh(.8*math.log(x['candidate']['cells']/x['baseline']['cells'])) for x in rows)/len(rows)
   else:
    r['objectives']=scores(rows);r['reward']=r['objectives'][c.objective]['reward'];r['objective_eligible']=r['objectives'][c.objective]['eligible']
    target=[ratios(x['baseline'],x['candidate']) for x in rows if x['target']]
    r['pareto_point']={key:math.exp(sum(math.log(x[key]) for x in target)/len(target)) for key in target[0]};r['baseline_relation']=relation(r['pareto_point'])
  except (Rejected,ValueError,OSError,AssertionError) as e:
   r.update(validation='rejected',reason='qualification failed')
   if artifacts:(Path(artifacts)/'private-error.txt').write_text(str(e))
  r['elapsed_s']=round(time.monotonic()-start,3)
  if artifacts:(Path(artifacts)/'result.json').write_text(json.dumps(r,indent=2)+'\n')
  return r


def work(c,x,y):
 if c.name in ('scan','topk'):return 0 if c.name=='topk' and ((x>>136)&7)==0 else ((x>>128)&((1<<c.lanes)-1)).bit_count()
 if c.name=='histogram':return sum(((x>>(128+8*i))&255)<c.depth for i in range(c.k))+((y>>128)&15).bit_count()
 if c.name=='ecc':return c.width
 if c.name=='crc':return 0 if y&(1<<33) else c.width//8
 if c.name=='freelist':return 0 if y&8 or x&8 else (y&7)+((x>>16)&0xffffffff).bit_count()
 return bits_mask(c,x).bit_count()
