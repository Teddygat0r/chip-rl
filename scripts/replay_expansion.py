"""Trusted-host replay of one retained expansion case; not full qualification."""
import argparse,json,importlib
from pathlib import Path
from chip_rl.expansion.spec import Config
from chip_rl.expansion.rtl import design
from chip_rl.evaluate import TrustedEvaluator,Rejected,digest
expansion=importlib.import_module('chip_rl.expansion.evaluate')
p=argparse.ArgumentParser();p.add_argument('artifact',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache');a=p.parse_args()
try:
 case=json.loads((a.artifact/'private-case.json').read_text());c=Config(**case['config']);source=(a.artifact/'candidate.sv').read_text();q=TrustedEvaluator(a.cache)
 provenance=next((p/'result.json' for p in a.artifact.parents if (p/'result.json').exists()),None)
 if provenance is None:raise Rejected('original qualification result required')
 prior=json.loads(provenance.read_text())
 recipe=digest(q.recipe_fingerprint+''.join(p.read_text() for p in sorted(Path(expansion.__file__).parent.glob('*.py'))))
 if prior['recipe_sha256']!=recipe or prior['tool_fingerprint']!=q.tool_fingerprint:raise Rejected('use the original evaluator package and toolchain')
 expected_source=digest(design(c)) if a.artifact.name=='baseline' else prior['source_sha256']
 if digest(source)!=expected_source:raise Rejected('retained source hash differs')
 sd,sm,_=q._synth(c,source);metrics=expansion.simulate(c,source,sd/'netlist.v',case['seed'],case['count'],a.output)
 print(json.dumps({'case_replay_passed':True,'qualification':'not_performed_by_single_case_replay','metrics':metrics,'synthesis':sm},indent=2))
except (Rejected,OSError,ValueError,KeyError) as e:
 print(json.dumps({'case_replay_passed':False,'qualification':'not_performed_by_single_case_replay','reason':str(e)}));raise SystemExit(1)
