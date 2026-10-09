"""Experimental balanced proxy for verified paired sparse24 cases."""
import math
from ..evaluate import Rejected

def positive(value,label):
 if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
  raise Rejected('invalid positive metric: '+label)
 return value

def validate_metrics(g,m,label):
 if not isinstance(m,dict):raise Rejected('missing '+label+' metrics')
 if m.get('rtl_mapped_checked') is not True or m.get('decoder_rtl_mapped_checked') is not True:
  raise Rejected('unverified '+label+' simulations')
 if m.get('decoder_vectors_checked')!=24*g:raise Rejected('incomplete decoder coverage')
 for field in ('cells','workload_cycles','stream_ii_numerator','stream_ii_denominator'):
  positive(m.get(field),label+' '+field)

def score_cases(cases):
 if not isinstance(cases,list) or not cases:raise Rejected('missing scored cases')
 rows=[];logs=[]
 for case in cases:
  if not isinstance(case,dict) or case.get('candidate_verified') is not True or case.get('baseline_verified') is not True:
   raise Rejected('missing verified paired metrics')
  g=case.get('G')
  if type(g) is not int or g not in range(1,9):raise Rejected('invalid scored G')
  ca=case.get('candidate');ba=case.get('baseline')
  validate_metrics(g,ca,'candidate');validate_metrics(g,ba,'baseline')
  area=positive(ca.get('cells'),'candidate cells')/positive(ba.get('cells'),'baseline cells')
  cycles=positive(ca.get('workload_cycles'),'candidate cycles')/positive(ba.get('workload_cycles'),'baseline cycles')
  num=positive(ca.get('stream_ii_numerator'),'candidate II numerator')
  den=positive(ca.get('stream_ii_denominator'),'candidate II denominator')
  positive(ba.get('stream_ii_numerator'),'baseline II numerator')
  positive(ba.get('stream_ii_denominator'),'baseline II denominator')
  ii=num/den
  if not all(math.isfinite(x) and x>0 for x in (area,cycles,ii)):raise Rejected('invalid paired ratio')
  gates={'area_ratio_at_most_4':area<=4,'completion_ratio_at_most_1':cycles<=1,
         'stream_ii_at_most_2G_plus_4':num<=(2*g+4)*den}
  rows.append({'G':g,'area_ratio':area,'completion_ratio':cycles,'stream_ii':ii,
               'stream_ii_limit':2*g+4,'constraints':gates,'constraints_passed':all(gates.values())})
  logs.append(math.log(area)+math.log(cycles))
 qualified=all(row['constraints_passed'] for row in rows)
 mean_log=math.fsum(logs)/len(logs)
 return {'reward':max(0.,1.-math.exp(mean_log/2)) if qualified else 0.,
         'reward_qualified':qualified,'hard_constraints_passed':qualified,
         'scored_cases':rows,'mean_log_area_cycle_product':mean_log,
         'constraint_failures':[{'G':row['G'],'failed':[k for k,v in row['constraints'].items() if not v]}
                                for row in rows if not row['constraints_passed']]}
