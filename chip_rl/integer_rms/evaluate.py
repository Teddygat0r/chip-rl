"""Paired exact RTL/mapped checks and conditional balanced proxy reward."""
from pathlib import Path
import fcntl,json,os,tempfile,time
from ..audit import journal
from ..evaluate import Rejected,digest,sanitize
from .spec import Config,NS,configurations,identity
from .rtl import design
from .synthesis import Synthesis
from .workloads import generate
from .arithmetic_check import check as arithmetic_check,selected
from .simulation import simulate
from .scoring import score_cases

def validate_metrics(m,key,work,n):
 if not isinstance(m,dict):raise Rejected('missing verified metrics')
 if not all(m.get(k) is True for k in ('rtl_mapped_checked','arithmetic_rtl_mapped_checked',
  'reset_backpressure_checked','long_stall_checked','reset_during_stall_checked',
  'long_stall_output_seen','reset_blocked_output_seen')):raise Rejected('incomplete verified probes')
 if m.get('arithmetic_vectors_checked')!=len(selected(work)) or m.get('arithmetic_vector_sha256')!=key['arithmetic_vector_sha256']:
  raise Rejected('arithmetic cache mismatch')
 if m.get('workload_sha256')!=work['sha256'] or m.get('watchdog_sha256')!=work['watchdog_sha256']:
  raise Rejected('workload cache mismatch')
 if m.get('accepted_count')!=m.get('consumed_count') or m.get('transactions')!=m.get('accepted_count'):
  raise Rejected('incomplete transaction record')
 if m.get('service_opportunity_bound')!=8*n+160 or m.get('stream_transactions')!=32 or m.get('cells',0)<1:
  raise Rejected('unverified measurement record')
 return m

def verified_cache(path,key,work,n):
 stored=json.loads(Path(path).read_text())
 if stored.get('identity')!=key or stored.get('verified') is not True:raise Rejected('unverified cache')
 return validate_metrics(stored.get('metrics'),key,work,n)

class Evaluator:
 def __init__(self,cache=None):self.synth=Synthesis(cache)
 @journal
 def evaluate(self,c:Config,source,*,replay_seed=None,artifacts=None,split='development'):
  root=Path(artifacts);start=time.monotonic()
  r={'task':'integer_rms','tested_correct':False,'validation':'rejected','reward':0.,
   'reward_qualified':False,'service_qualified':False,'hard_constraints_passed':False,
   'measurement_only':False,'split':split,'N':c.n,'declared_scored_Ns':NS,
   'declared_measured_Ns':tuple(sorted(set(NS)|{c.n})),
   'source_sha256':digest(source) if isinstance(source,str) else None,
   'contract_sha256':identity(c),'tool_fingerprint':self.synth.host.tool_fingerprint,
   'formal':'not_run','physical':'not_run','independent_evaluation':False,'os_isolation':'not_provided',
   'candidate':None,'baseline':None,'cases':[],'scored_cases':[],'constraint_failures':[],
   'baseline_simulation_cache_hits':0,'candidate_simulation_cache_hits':0}
  r['recipe_sha256']=digest(''.join(p.read_text() for p in sorted(Path(__file__).parent.glob('*'))
                                 if p.suffix in ('.py','.md'))+self.synth.host.recipe_fingerprint)
  try:
   if type(c) is not Config or type(replay_seed) is not int or not 0<=replay_seed<2**128 or split not in ('development','heldout'):
    raise Rejected('invalid trusted evaluation request')
   sanitize(source);baseline=design('serial')
   for n in configurations(split,c.n):
    work=generate(n,(replay_seed+n)%(1<<128),split)
    case={'N':n,'candidate_verified':False,'baseline_verified':False}
    r['cases'].append(case)
    for label,src in (('candidate',source),('baseline',baseline)):
     if label=='baseline' and source==baseline:
      case[label]=dict(case['candidate']);case[label+'_verified']=True;continue
     key={'source_sha256':digest(src),'N':n,'tool_fingerprint':self.synth.host.tool_fingerprint,
      'recipe_sha256':r['recipe_sha256'],'contract_sha256':identity(c),
      'workload_sha256':work['sha256'],'watchdog_sha256':work['watchdog_sha256'],
      'arithmetic_vector_sha256':digest(json.dumps(selected(work)))}
     path=self.synth.root/('integer-rms-verified-'+digest(json.dumps(key,sort_keys=True))+'.json')
     with path.with_suffix('.lock').open('a') as lock:
      fcntl.flock(lock,fcntl.LOCK_EX)
      if path.exists():
       case[label]=verified_cache(path,key,work,n);case[label+'_verified']=True
       r[label+'_simulation_cache_hits']+=1;continue
     build,structural=self.synth.compile(n,src)
     d=root/f'n{n}'/label;d.mkdir(parents=True)
     for name in ('synth.ys','netlist.json'):(d/name).write_bytes((build/name).read_bytes())
     arithmetic=arithmetic_check(n,src,build/'netlist.v',work,d/'arithmetic')
     measured=simulate(n,src,build/'netlist.v',work,d/'simulation')
     case[label]=validate_metrics(structural|arithmetic|measured,key,work,n)
     case[label+'_verified']=True
     with path.with_suffix('.lock').open('a') as lock:
      fcntl.flock(lock,fcntl.LOCK_EX)
      fd,name=tempfile.mkstemp(prefix='integer-rms-verified-',dir=self.synth.root)
      try:
       with os.fdopen(fd,'w') as f:
        json.dump({'identity':key,'verified':True,'metrics':case[label]},f);f.flush();os.fsync(f.fileno())
       os.replace(name,path)
      finally:
       if os.path.exists(name):os.unlink(name)
    if n==c.n:r['candidate']=case['candidate'];r['baseline']=case['baseline']
   if not all(x['candidate_verified'] and x['baseline_verified'] for x in r['cases']):raise Rejected('incomplete paired validation')
   scoring=score_cases([case for case in r['cases'] if case['N'] in NS])
   r.update(tested_correct=True,validation='exact_integer_rtl_mapped_pass')
   r.update(scoring)
  except (Rejected,ValueError,OSError,AssertionError,TypeError,KeyError) as e:
   (root/'private-error.txt').write_text(str(e))
  r['elapsed_s']=round(time.monotonic()-start,3)
  (root/'result.json').write_text(json.dumps(r,indent=2)+'\n')
  return r
