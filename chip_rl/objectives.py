"""Explicit fixed host objectives. Scores never hide their feasibility gates."""
import math
PROFILES={
 'area':{'weights':(.8,.15,.05),'max_cycle_ratio':16.,'max_latency_ratio':1024.},
 'balanced':{'weights':(.45,.30,.25),'max_cycle_ratio':2.,'max_latency_ratio':4.},
 'latency':{'weights':(.20,.25,.55),'max_cycle_ratio':1.1,'max_latency_ratio':1.1},
}
def ratios(base,candidate):
 return {'cells':candidate['cells']/base['cells'],'cycles':candidate['cycles']/base['cycles'],
         'latency':(candidate['offered_latency']+1)/(base['offered_latency']+1)}
def scores(rows):
 result={}
 for name,p in PROFILES.items():
  eligible=all((r:=ratios(x['baseline'],x['candidate']))['cycles']<=p['max_cycle_ratio'] and r['latency']<=p['max_latency_ratio'] for x in rows)
  values=[]
  for x in rows:
   if x['target']:
    r=ratios(x['baseline'],x['candidate']);loss=sum(w*math.log(r[k]) for w,k in zip(p['weights'],('cells','cycles','latency')))
    values.append(1-.5*math.tanh(loss))
  result[name]={'eligible':eligible,'reward':sum(values)/len(values) if eligible else 0.,'limits':dict(p)}
 return result
def relation(r):
 vals=list(r.values())
 if all(abs(x-1)<1e-12 for x in vals):return 'equal_to_baseline'
 if all(x<=1+1e-12 for x in vals):return 'dominates_baseline'
 if all(x>=1-1e-12 for x in vals):return 'dominated_by_baseline'
 return 'area_performance_tradeoff'
def frontier(points):
 return [name for name,a in points.items() if not any(all(b[k]<=a[k] for k in a) and any(b[k]<a[k] for k in a) for other,b in points.items() if other!=name)]
