"""Full final-source controlled acceptance/fault matrix for the v20 audit."""
import argparse,json,shutil
from pathlib import Path
from chip_rl.layout.spec import Config
from chip_rl.layout.audit_cases import correct,bad
from chip_rl.layout.evaluate import Evaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[];q=Evaluator(a.cache)
jobs=[(f'{objective}-{split}-{name}',Config(objective=objective),correct(name),split,True) for objective in ('transpose','diagonal') for split in ('development','heldout','reserve') for name in ('row_major','xor','add')]
jobs += [(f'transpose-{split}-column_major',Config(),correct('column_major'),split,True) for split in ('development','heldout','reserve')]
jobs += [(f'syntax-{name}',Config(),correct(name),'development',True) for name in ('wildcard','always_comb','function')]
jobs += [(f'bad-{name}',Config(),bad(name),'heldout' if name=='unmasked_row' else 'development',False) for name in ('alias','out_of_range','drop_high_col','unmasked_row','padding','latch','port','divergence','manual_sensitivity','extra_read_port','hidden_state','uncounted_rom','attribute')]
for name,c,source,split,want in jobs:
 if shutil.disk_usage(a.output).free<300*1024**2:raise SystemExit('disk budget')
 r=q.evaluate(c,source,replay_seed=190190,artifacts=a.output/name,split=split);rows.append({'case':name,'expected_correct':want,'result':r});(a.output/'results.json').write_text(json.dumps(rows,indent=2));print(name,r['tested_correct'],round(r['reward'],5),r['elapsed_s'],flush=True);assert r['tested_correct']==want,name
assert len(rows)==37
