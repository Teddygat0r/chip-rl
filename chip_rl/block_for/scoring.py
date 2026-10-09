"""Fixed balanced generic-cell/completion proxy and independent II gate."""
import math
from ..evaluate import Rejected
from .spec import NS, SUPPORTED_NS

def positive(value,label):
 if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
  raise Rejected('invalid positive metric: '+label)
 return value

def checked_metrics(n,metrics,label):
 if not isinstance(metrics,dict):raise Rejected('missing '+label+' metrics')
 if metrics.get('rtl_mapped_checked') is not True or metrics.get('exact_rtl_mapped_checked') is not True:
  raise Rejected('unverified '+label+' simulations')
 if type(metrics.get('exact_vectors_checked')) is not int or metrics['exact_vectors_checked']<20:
  raise Rejected('incomplete '+label+' exact probes')
 for field in ('cells','workload_cycles','stream_ii_numerator','stream_ii_denominator'):
  positive(metrics.get(field),label+' '+field)

def score_cases(cases):
 if not isinstance(cases,list) or len(cases)!=len(NS) or {c.get('N') for c in cases if isinstance(c,dict)}!=set(NS):
  raise Rejected('missing or duplicate scored N')
 rows=[];logs=[]
 for case in cases:
  if not isinstance(case,dict) or case.get('candidate_verified') is not True or case.get('baseline_verified') is not True:
   raise Rejected('missing verified paired metrics')
  n=case.get('N')
  if type(n) is not int or n not in SUPPORTED_NS:raise Rejected('invalid scored N')
  ca=case.get('candidate');ba=case.get('baseline')
  checked_metrics(n,ca,'candidate');checked_metrics(n,ba,'baseline')
  area=ca['cells']/ba['cells'];cycles=ca['workload_cycles']/ba['workload_cycles']
  ii=ca['stream_ii_numerator']/ca['stream_ii_denominator']
  if not all(math.isfinite(x) and x>0 for x in (area,cycles,ii)):raise Rejected('invalid paired ratio')
  gates={'area_ratio_at_most_4':area<=4,'completion_ratio_at_most_1':cycles<=1,
         'stream_ii_at_most_2N_plus_6':ca['stream_ii_numerator']<=(2*n+6)*ca['stream_ii_denominator']}
  rows.append({'N':n,'area_ratio':area,'completion_ratio':cycles,'stream_ii':ii,
               'stream_ii_limit':2*n+6,'constraints':gates,'constraints_passed':all(gates.values())})
  logs.append(math.log(area)+math.log(cycles))
 qualified=all(row['constraints_passed'] for row in rows)
 mean_log=math.fsum(logs)/len(logs)
 return {'reward':max(0.,1.-math.exp(mean_log/2)) if qualified else 0.,
         'reward_qualified':qualified,'service_qualified':qualified,'hard_constraints_passed':qualified,
         'scored_cases':rows,'mean_log_area_cycle_product':mean_log,
         'constraint_failures':[{'N':row['N'],'failed':[k for k,v in row['constraints'].items() if not v]}
                                for row in rows if not row['constraints_passed']]}
