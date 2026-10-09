"""Experimental paired fused evaluation with a gated proxy reward."""
from pathlib import Path
import json,time
from ..audit import journal
from ..evaluate import Rejected,digest,sanitize
from .spec import Config,configurations,identity
from .rtl import design
from .synthesis import Synthesis
from .workloads import generate
from .simulation import simulate
from .scoring import score_cases

class Evaluator:
 def __init__(self,cache=None):self.synth=Synthesis(cache)
 @journal
 def evaluate(self,c:Config,source,*,replay_seed=None,artifacts=None,split='development'):
  root=Path(artifacts);start=time.monotonic()
  result={'task':'fused_dot_requant','tested_correct':False,'validation':'rejected','reward':0.0,'reward_qualified':False,'split':split,'K':c.k,
   'source_sha256':digest(source) if isinstance(source,str) else None,'contract_sha256':identity(c),'tool_fingerprint':self.synth.host.tool_fingerprint,
   'formal':'not_run','physical':'not_run','independent_evaluation':False,'os_isolation':'not_provided','candidate':None,'baseline':None,
   'scored_cases':[],'constraint_failures':[],'hard_constraints_passed':None,'cases':[],'declared_scored_Ks':[]}
  result['recipe_sha256']=digest(''.join(p.read_text() for p in sorted(Path(__file__).parent.glob('*')) if p.suffix in ('.py','.md'))+self.synth.host.recipe_fingerprint)
  try:
   if type(c) is not Config or type(replay_seed) is not int or not 0<=replay_seed<2**128 or split not in ('development','heldout'):raise Rejected('invalid trusted evaluation request')
   sanitize(source)
   declared=tuple(sorted(set(configurations(split))|{c.k}))
   result['declared_scored_Ks']=declared
   baseline=design('serial')
   for k in declared:
    # Preserve the v28 operand/release/readiness prefixes for the same trusted
    # replay root: development used one seed; heldout used root+K.
    case_seed=replay_seed if split=='development' else (replay_seed+k)%(1<<128)
    w=generate(k,case_seed,split)
    case={'K':k,'candidate_verified':False,'baseline_verified':False}
    result['cases'].append(case)
    for label,src in (('candidate',source),('baseline',baseline)):
     if label=='baseline' and source==baseline:
      case[label]=dict(case['candidate']);case[label+'_verified']=True;continue
     build,structural=self.synth.compile(k,src)
     d=root/f'k{k}'/label
     d.mkdir(parents=True)
     for name in ('synth.ys','netlist.json'):(d/name).write_bytes((build/name).read_bytes())
     measured=simulate(k,src,build/'netlist.v',w,d/'simulation')
     case[label]=structural|measured;case[label+'_verified']=True
    if k==c.k:result['candidate']=case['candidate'];result['baseline']=case['baseline']
   score=score_cases(result['cases'])
   result.update(tested_correct=True,validation='rtl_and_mapped_exact_pass',**score)
  except (Rejected,ValueError,OSError,AssertionError,TypeError,KeyError) as e:(root/'private-error.txt').write_text(str(e))
  result['elapsed_s']=round(time.monotonic()-start,3)
  (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  return result
