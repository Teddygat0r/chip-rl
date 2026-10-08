"""Correctness and structural qualification before paired digital cost rewards."""
import json,secrets,time,tempfile,math
from ..audit import journal
from pathlib import Path
from dataclasses import asdict
from ..evaluate import Rejected,digest
from .spec import Config,Choice,specification,identity,configurations
from .rtl import design
from .synthesis import Synthesis
from .workloads import make
from .simulation import simulate
class Evaluator:
 def __init__(self,cache=None):self.synth=Synthesis(cache)
 @journal
 def evaluate(self,c,choice=Choice(),*,replay_seed=None,artifacts=None,trusted_source=None,heldout=False):
  if not isinstance(c,Config) or not isinstance(choice,Choice):raise ValueError('trusted configuration and choice required')
  seed=secrets.randbits(128) if replay_seed is None else replay_seed
  if type(seed) is not int or not 0<=seed<2**128:raise ValueError('host replay seed')
  source=design(choice) if trusted_source is None else trusted_source;start=time.monotonic()
  result={**specification(c),'choice':asdict(choice),'tested_correct':False,'reward':0.,'contract_sha256':identity(c),'source_sha256':digest(source) if isinstance(source,str) else None,'recipe_sha256':digest(''.join(p.read_text() for p in sorted(Path(__file__).parent.glob('*.py')))),'tool_fingerprint':self.synth.host.tool_fingerprint,'cases':[],'heldout':heldout}
  if artifacts:Path(artifacts).mkdir(parents=True,exist_ok=True);Path(artifacts).chmod(0o700)
  try:
   with tempfile.TemporaryDirectory(prefix='chip-cdc-') as td:
    root=Path(artifacts) if artifacts else Path(td)
    (root/'candidate.sv').write_text(source)
    (root/'private-seed.json').write_text(json.dumps({'seed':seed}))
    for i,cc in enumerate(configurations(c)):
     sd,sm=self.synth.compile(cc,choice,source);epochs=make(cc,seed+i,heldout)
     cm=simulate(cc,source,sd/'netlist.v',epochs,root/f'case-{i}'/'candidate')|sm
     base=Choice();base_source=design(base)
     if source==base_source:bm=dict(cm)
     else:
      bd,bsm=self.synth.compile(cc,base,base_source);bm=simulate(cc,base_source,bd/'netlist.v',epochs,root/f'case-{i}'/'baseline')|bsm
     if cm['vectors_sha256']!=bm['vectors_sha256']:raise Rejected('unpaired CDC vectors')
     result['cases'].append({'config':asdict(cc),'candidate':cm,'baseline':bm})
    ratios={k:math.exp(sum(math.log(row['candidate'][k]/row['baseline'][k]) for row in result['cases'])/len(result['cases'])) for k in ('cells','ticks','latency_sum')}
    eligible=all(row['candidate']['ticks']<=2*row['baseline']['ticks'] and row['candidate']['latency_sum']<=2*row['baseline']['latency_sum'] for row in result['cases'])
    loss=.65*math.log(ratios['cells'])+.25*math.log(ratios['ticks'])+.10*math.log(ratios['latency_sum'])
    result.update(tested_correct=True,objective_eligible=eligible,reward=1-.5*math.tanh(loss) if eligible else 0.,ratios=ratios,objective={'area_weight':.65,'ticks_weight':.25,'latency_weight':.10,'max_tick_ratio':2,'max_latency_ratio':2,'latency_measure':'accepted-write to accepted-read in abstract event ticks','physical_frequency_claim':False},validation='structural_and_rtl_and_mapped_pass')
  except (Rejected,ValueError,OSError,AssertionError) as e:
   result['validation']='rejected'
   if artifacts:(Path(artifacts)/'private-error.txt').write_text(str(e))
  result['elapsed_s']=round(time.monotonic()-start,3)
  if artifacts:(Path(artifacts)/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  return result
