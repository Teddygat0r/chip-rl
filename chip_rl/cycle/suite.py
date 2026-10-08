"""Qualification of experimental cycle controllers, not promotion to pilot status."""
import argparse,json
from pathlib import Path
from ..tasks import Config
from ..suite import compact
from .rtl import design
from .evaluate import CycleEvaluator

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');p.add_argument('--tasks',nargs='+',default=['dma','router','scoreboard','accelerator']);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False);a.output.chmod(0o700);q=CycleEvaluator(a.cache);rows={};fail=[]
 for n in a.tasks:
  c=Config(n,depth=16);rows[n]={};mutants=['zero','clock','drop','stall','no_reset','late_drop']
  if n in ('router','scoreboard'):mutants+=['unfair']
  if n=='dma':mutants+=['bad_data']
  if n=='accelerator':mutants+=['no_overlap']
  cases=[('baseline',design(c),True),('alternate',design(c,alternate=True),True),('pruned',design(c,alternate='pruned'),True)]+[(x,design(c,mutant=x),False) for x in mutants]
  if n=='router':cases.insert(3,('decoded',design(c,alternate='decoded'),True))
  for label,src,expected in cases:
   path=a.output/n/label;r=q.evaluate(c,src,replay_seed=99173,artifacts=path);compact(path);rows[n][label]=r
   if r['tested_correct']!=expected:fail.append(n+'/'+label)
   print(n,label,'PASS' if r['tested_correct']==expected else 'FAIL',r.get('reason',''),flush=True)
   (a.output/'summary.json').write_text(json.dumps({'tasks':rows,'failures':fail,'scope':'experimental fixed-cycle controllers, not promoted'},indent=2)+'\n')
 if fail:raise SystemExit(1)
if __name__=='__main__':main()
