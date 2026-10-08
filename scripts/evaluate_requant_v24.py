from pathlib import Path
import argparse,json
from chip_rl.requant.evaluate import Evaluator
from chip_rl.requant.spec import Config
from chip_rl.requant.rtl import design,bad
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--split',default='development');p.add_argument('--bad',action='store_true');p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',required=True);p.add_argument('--ledger',type=Path,required=True);a=p.parse_args()
w=a.root;w.mkdir(parents=True,exist_ok=True);ledger=a.ledger;r=json.loads(ledger.read_text());calls=r.setdefault('calls',[])
assert len(calls)<50 and not (w/a.name).exists()
logs=list(w.rglob('tool-logs/*.log'));syn=sum('requant-synthesis-' in x.name for x in logs);sim=sum('simulation-' in x.name for x in logs)
assert syn+4<=100 and sim+8<=600
calls.append({'name':a.name,'split':a.split,'status':'started'});ledger.write_text(json.dumps(r,indent=2))
label=a.name.split('__')[0];source=bad(label) if a.bad else design(label)
result=Evaluator(a.cache).evaluate(Config(),source,replay_seed=240024,artifacts=w/a.name,split=a.split)
r=json.loads(ledger.read_text());r['calls'][-1]['status']='completed';r['calls'][-1]['correct']=result['tested_correct'];ledger.write_text(json.dumps(r,indent=2));print(a.name,result['tested_correct'],result['reward'],result.get('ratios'));assert result['tested_correct']!=a.bad
