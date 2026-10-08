"""Host-only exact replay; preserve every qualification field except elapsed seconds."""
import argparse,json
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.evaluate import Evaluator
from chip_rl.suite import compact

def signature(r):return json.dumps({k:v for k,v in r.items() if k!='elapsed_s'},sort_keys=True,separators=(',',':'),allow_nan=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args()
 if a.output.exists():raise ValueError('new output directory required')
 j=json.loads((a.artifact/'private-run.json').read_text());before=json.loads((a.artifact/'result.json').read_text())
 after=Evaluator(a.cache).evaluate(Config(**j['config']),(a.artifact/'candidate.sv').read_text(),replay_seed=j['seed'],heldout=before['heldout'],artifacts=a.output)
 assert signature(before)==signature(after),'qualification replay differs'
 compact(a.output);print(json.dumps({'replayed':True,'tested_correct':after['tested_correct'],'task':j['config']['name'],'identical':'all qualification fields including source, contract, recipe, tools, vectors, metrics and gates; elapsed_s excluded'}))
if __name__=='__main__':main()
