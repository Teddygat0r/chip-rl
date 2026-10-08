"""Compare the final full matrix against v19's exact same scored source/seed/config."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--current',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();old=json.loads((a.prior/'results.json').read_text());new={r['case']:r for r in json.loads((a.current/'results.json').read_text())};rows=[]
for row in old:
 if not row['expected_correct']:continue
 name=row['case'];current='diagonal-development-'+name[len('diagonal-'):] if name.startswith('diagonal-') else 'transpose-'+name
 x=row['result'];y=new[current]['result'];j0=json.loads((a.prior/name/'private-run.json').read_text());j1=json.loads((a.current/current/'private-run.json').read_text());assert j0['seed']==j1['seed'] and j0['config']==j1['config']
 for key in ('tested_correct','source_sha256','reward','cases','service_speedup_geomean','mean_mapper_cells','tool_fingerprint'):assert x[key]==y[key],(name,key)
 assert y['verification'] and all(not r['included_in_reward'] for r in y['verification']);rows.append(name)
a.output.write_text(json.dumps({'exact_scored_results_unchanged':True,'matched_cases':rows,'scope':'same source/config/private seed/tool fingerprint; directed probes and cancellation are unscored'},indent=2));print('PASS',len(rows),'exact paired score comparisons')
