"""Finite paired sparse24 RTL/mapped checks and experimental proxy reward."""
from pathlib import Path
import json,time,fcntl,os,tempfile
from ..audit import journal
from ..evaluate import Rejected,digest,sanitize
from .spec import Config,configurations,identity
from .rtl import design
from .synthesis import Synthesis
from .workloads import generate
from .simulation import simulate
from .decoder_check import check as decoder_check,vectors as decoder_vectors
from .scoring import score_cases,validate_metrics

def verified_cache(path,cache_identity,g,work,label):
 stored=json.loads(Path(path).read_text())
 if stored.get('identity')!=cache_identity or stored.get('verified') is not True:
  raise Rejected(label+' cache identity mismatch or unverified')
 metrics=stored.get('metrics')
 validate_metrics(g,metrics,label)
 if (metrics.get('workload_sha256')!=work['sha256'] or
     metrics.get('watchdog_sha256')!=work['watchdog_sha256'] or
     metrics.get('decoder_vector_sha256')!=cache_identity['decoder_vector_sha256']):
  raise Rejected(label+' cache workload mismatch')
 return metrics

class Evaluator:
 def __init__(self,cache=None):self.synth=Synthesis(cache)
 @journal
 def evaluate(self,c:Config,source,*,replay_seed=None,artifacts=None,split='development'):
  root=Path(artifacts);start=time.monotonic()
  result={'task':'sparse24_dot_requant','tested_correct':False,'validation':'rejected','reward':0.,'reward_qualified':False,'hard_constraints_passed':False,
   'split':split,'G':c.g,'source_sha256':digest(source) if isinstance(source,str) else None,
   'contract_sha256':identity(c),'tool_fingerprint':self.synth.host.tool_fingerprint,
   'formal':'not_run','physical':'not_run','independent_evaluation':False,'os_isolation':'not_provided',
   'candidate':None,'baseline':None,'cases':[],'declared_scored_Gs':[],'scored_cases':[],
   'baseline_simulation_cache_hits':0,'candidate_simulation_cache_hits':0}
  result['recipe_sha256']=digest(''.join(p.read_text() for p in sorted(Path(__file__).parent.glob('*')) if p.suffix in ('.py','.md'))+self.synth.host.recipe_fingerprint)
  try:
   if type(c) is not Config or type(replay_seed) is not int or not 0<=replay_seed<2**128 or split not in ('development','heldout'):
    raise Rejected('invalid trusted evaluation request')
   sanitize(source)
   declared=tuple(sorted(set(configurations(split))|{c.g}));result['declared_scored_Gs']=declared
   baseline=design('serial')
   for g in declared:
    case_seed=replay_seed if split=='development' else (replay_seed+g)%(1<<128)
    work=generate(g,case_seed,split)
    case={'G':g,'candidate_verified':False,'baseline_verified':False}
    result['cases'].append(case)
    for label,src in (('candidate',source),('baseline',baseline)):
     if label=='baseline' and source==baseline:
      case[label]=dict(case['candidate']);case[label+'_verified']=True;continue
     cache_identity={'source_sha256':digest(src),'G':g,'tool_fingerprint':self.synth.host.tool_fingerprint,
       'recipe_sha256':result['recipe_sha256'],'contract_sha256':identity(c),
       'workload_sha256':work['sha256'],'watchdog_sha256':work['watchdog_sha256'],
       'decoder_vector_sha256':digest(json.dumps(decoder_vectors(g)[0]))}
     cache_path=self.synth.root/('sparse24-verified-'+digest(json.dumps(cache_identity,sort_keys=True))+'.json')
     with cache_path.with_suffix('.lock').open('a') as lock:
      fcntl.flock(lock,fcntl.LOCK_EX)
      if cache_path.exists():
       metrics=verified_cache(cache_path,cache_identity,g,work,label)
       case[label]=metrics;case[label+'_verified']=True
       result[label+'_simulation_cache_hits']=result.get(label+'_simulation_cache_hits',0)+1
       continue
     build,structural=self.synth.compile(g,src)
     d=root/f'g{g}'/label;d.mkdir(parents=True)
     for name in ('synth.ys','netlist.json'):(d/name).write_bytes((build/name).read_bytes())
     decoder=decoder_check(g,src,build/'netlist.v',d/'decoder')
     measured=simulate(g,src,build/'netlist.v',work,d/'simulation')
     case[label]=structural|decoder|measured;case[label+'_verified']=True
     with cache_path.with_suffix('.lock').open('a') as lock:
      fcntl.flock(lock,fcntl.LOCK_EX)
      fd,name=tempfile.mkstemp(prefix='sparse24-verified-',dir=self.synth.root)
      try:
       with os.fdopen(fd,'w') as f:
        json.dump({'identity':cache_identity,'verified':True,'metrics':case[label]},f);f.flush();os.fsync(f.fileno())
       os.replace(name,cache_path)
      finally:
       if os.path.exists(name):os.unlink(name)
    if g==c.g:result['candidate']=case['candidate'];result['baseline']=case['baseline']
   scoring=score_cases(result['cases'])
   result.update(tested_correct=True,validation='rtl_and_mapped_exact_pass')
   result.update(scoring)
  except (Rejected,ValueError,OSError,AssertionError,TypeError,KeyError) as e:
   (root/'private-error.txt').write_text(str(e))
  result['elapsed_s']=round(time.monotonic()-start,3)
  (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  return result
