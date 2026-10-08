"""Trusted-host pilot release qualification; evidence is private, never agent input."""
import argparse,gzip,json,shutil,time,resource
from pathlib import Path
from .tasks import Config
from .contracts import PILOT,EXPERIMENTAL
from .rtl import design
from .architectures import architecture,CATALOG
from .adversaries import mutant,labels
from .evaluate import TrustedEvaluator

def compact(path):
    for p in path.rglob('*'):
        if not p.is_file():continue
        if p.suffix=='.vvp':p.unlink()
        elif p.name in ('netlist.json','netlist.v') or p.suffix=='.log':
            with p.open('rb') as src,gzip.open(str(p)+'.gz','wb') as dst:shutil.copyfileobj(src,dst)
            p.unlink()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--cache');ap.add_argument('--tasks',nargs='+',choices=PILOT,default=list(PILOT));ap.add_argument('--seed',type=int,default=20261006);a=ap.parse_args()
    root=Path(a.output);root.mkdir(parents=True,exist_ok=False);root.chmod(0o700)
    q=TrustedEvaluator(a.cache);rows={};failures=[];started=time.monotonic()
    for name in a.tasks:
        c=Config(name);rows[name]={}
        cases=[(label,architecture(c,label),True) for label in CATALOG[name]]
        bad=labels(name)
        cases += [('bad_'+label,mutant(c,label),False) for label in bad]
        for label,src,expected in cases:
            path=root/name/label
            r=q.evaluate(c,src,replay_seed=a.seed,artifacts=path)
            compact(path);rows[name][label]=r
            if r['tested_correct']!=expected:failures.append(name+'/'+label)
            print(name,label,'PASS' if r['tested_correct']==expected else 'FAIL',round(r['reward'],4),r.get('reason',''),flush=True)
            report={'tasks':rows,'failures':failures,'excluded':list(EXPERIMENTAL),'elapsed_s':time.monotonic()-started,'child_cpu_s':sum(resource.getrusage(resource.RUSAGE_CHILDREN)[:2])}
            (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    report['counts']={'functional_and_synthesis_families':sum(all(r['tested_correct'] for k,r in cases.items() if not k.startswith('bad_')) for cases in rows.values()),
        'adversaries_rejected':sum(not r['tested_correct'] for cases in rows.values() for k,r in cases.items() if k.startswith('bad_')),
        'formal_unbounded_families':0,'physical_families':0}
    (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['counts']),flush=True)
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
