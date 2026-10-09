"""Experimental balanced proxy objective for verified paired fused cases."""
import math
from ..evaluate import Rejected

AREA_RATIO_LIMIT=4
CYCLE_RATIO_LIMIT=1

def _positive_number(value,label):
 if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
  raise Rejected('invalid positive metric: '+label)
 return value

def score_cases(cases):
 """Equally weight every declared scored case; probes never enter this input."""
 if not isinstance(cases,list) or not cases:raise Rejected('missing scored cases')
 rows=[];logs=[]
 for case in cases:
  if not isinstance(case,dict) or case.get('baseline_verified') is not True or case.get('candidate_verified') is not True:
   raise Rejected('missing verified paired metrics')
  k=case.get('K')
  if type(k) is not int or k not in (1,2,4,8,16):raise Rejected('invalid scored K')
  candidate=case.get('candidate');baseline=case.get('baseline')
  if not isinstance(candidate,dict) or not isinstance(baseline,dict):raise Rejected('missing paired metrics')
  ca=_positive_number(candidate.get('cells'),'candidate cells')
  ba=_positive_number(baseline.get('cells'),'baseline cells')
  cc=_positive_number(candidate.get('workload_cycles'),'candidate cycles')
  bc=_positive_number(baseline.get('workload_cycles'),'baseline cycles')
  num=_positive_number(candidate.get('stream_ii_numerator'),'candidate II numerator')
  den=_positive_number(candidate.get('stream_ii_denominator'),'candidate II denominator')
  _positive_number(baseline.get('stream_ii_numerator'),'baseline II numerator')
  _positive_number(baseline.get('stream_ii_denominator'),'baseline II denominator')
  ra=ca/ba;rc=cc/bc;ii=num/den
  if not all(math.isfinite(x) and x>0 for x in (ra,rc,ii)):raise Rejected('invalid paired ratio')
  gates={'area_ratio_at_most_4':ra<=AREA_RATIO_LIMIT,'completion_ratio_at_most_1':rc<=CYCLE_RATIO_LIMIT,'stream_ii_at_most_K_plus_4':num<=(k+4)*den}
  rows.append({'K':k,'area_ratio':ra,'completion_ratio':rc,'stream_ii':ii,'stream_ii_limit':k+4,'constraints':gates,'constraints_passed':all(gates.values())})
  logs.append(math.log(ra)+math.log(rc))
 qualified=all(row['constraints_passed'] for row in rows)
 mean_log_product=math.fsum(logs)/len(logs)
 raw=max(0.,1.-math.exp(mean_log_product/2)) if qualified else 0.
 return {'reward':raw,'reward_qualified':qualified,'hard_constraints_passed':qualified,'scored_cases':rows,'mean_log_area_cycle_product':mean_log_product,
  'constraint_failures':[{'K':row['K'],'failed':[name for name,passed in row['constraints'].items() if not passed]} for row in rows if not row['constraints_passed']]}
