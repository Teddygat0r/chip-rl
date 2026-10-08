"""Exact host-only replay of one search measurement, excluding timing/cache counters."""
import argparse,json
from pathlib import Path
from chip_rl.tasks import Config
from chip_rl.evaluate import TrustedEvaluator
from chip_rl.memory.spec import Config as MemoryConfig
from chip_rl.memory.evaluate import Evaluator as MemoryEvaluator
from chip_rl.suite import compact
def qualification_signature(result):
 operational={'elapsed_s','synthesis_cache_hits','baseline_simulation_cache_hits'}
 # Evaluator Python tuples become JSON arrays in saved evidence. Compare the
 # canonical public representation without dropping any qualification fields.
 return json.dumps({k:v for k,v in result.items() if k not in operational},sort_keys=True,separators=(',',':'),allow_nan=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args()
 if a.output.exists():raise ValueError('new output required')
 j=json.loads((a.artifact/'private-run.json').read_text());before=json.loads((a.artifact/'result.json').read_text());src=(a.artifact/'candidate.sv').read_text();name=j['config']['name']
 if name not in ('tlb','dot','tensor'):raise ValueError('not a search task')
 args={'replay_seed':j['seed'],'artifacts':a.output}
 if name=='tlb':q=MemoryEvaluator(a.cache);c=MemoryConfig(**j['config']);args['heldout']=before['heldout']
 else:q=TrustedEvaluator(a.cache);c=Config(**j['config'])
 after=q.evaluate(c,src,**args)
 assert qualification_signature(before)==qualification_signature(after)
 assert after['tested_correct'];compact(a.output)
 print(json.dumps({'replayed':True,'task':name,'scope':'all public qualification fields identical except elapsed time and cache-hit counters; private seed/source retained'}))
if __name__=='__main__':main()
