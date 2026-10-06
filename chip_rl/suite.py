"""Reproducible release qualification; no success if any required case fails."""
import argparse, dataclasses, gzip, json, shutil
from pathlib import Path
from .tasks import Config,NAMES
from .rtl import design
from .alternates import alternate
from .mutants import semantic
from .evaluate import evaluate,tool
from .formal import check_elastic

def compact(path):
    # Preserve source, vectors, harness and tool logs. Recreate binaries by replay.
    for p in path.iterdir():
        if p.suffix=='.vvp': p.unlink()
        elif p.name in ('netlist.json','netlist.v') or p.suffix=='.log':
            with p.open('rb') as src,gzip.open(str(p)+'.gz','wb') as dst: shutil.copyfileobj(src,dst)
            p.unlink()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='artifacts/release');ap.add_argument('--tasks',nargs='*',default=list(NAMES));args=ap.parse_args()
    root=Path(args.output);root.mkdir(parents=True,exist_ok=False);results={};failures=[]
    for name in args.tasks:
        c=Config(name);base=None;rows={}
        cases=[('baseline',c,design(c),1,'train'),('alternate',c,alternate(c),1,'train'),
               ('heldout',c,alternate(c),982451653,'challenge'),
               ('structural',dataclasses.replace(c,width=24,depth=16,k=2),None,32452843,'challenge'),
               ('semantic_bad',c,semantic(c),1,'train'),('drop_bad',c,design(c,mutant='drop'),1,'train'),
               ('stall_bad',c,design(c,mutant='unstable'),1,'train')]
        for label,conf,source,seed,split in cases:
            source=source or alternate(conf);path=root/name/label
            r=evaluate(conf,source,seed=seed,split=split,count=128,artifacts=path,baseline=base if label=='alternate' else None)
            compact(path);rows[label]=r
            expected=not label.endswith('_bad')
            if r['correct']!=expected: failures.append(name+'/'+label+': '+str(r.get('error')))
            if label=='baseline': base=r
            if label=='alternate' and r['correct'] and r['reward']<=1.: failures.append(name+'/reward not sensitive')
            print(name,label,'PASS' if r['correct']==expected else 'FAIL',r.get('cells','-'),round(r['reward'],4),flush=True)
        results[name]=rows
        (root/'summary.json').write_text(json.dumps({'tasks':results,'failures':failures},indent=2)+'\n')
    formal={}
    for label,stages,mutant in [('baseline',4,None),('alternate',2,None),('bad',2,'corrupt')]:
        path=root/('formal-'+label)
        src=alternate(Config('elastic',width=8),stages) if label=='alternate' else design(Config('elastic',width=8),stages,mutant)
        r=check_elastic(src,artifacts=path);compact(path);formal[label]=r
        if (r['status']=='bounded_pass') != (mutant is None): failures.append('formal/'+label)
    counts={stage:sum(all(rows[k][stage]=='pass' for k in ('baseline','alternate','heldout','structural')) for rows in results.values()) for stage in ('functional','synthesis','netlist')}
    counts.update({'formal_bounded_families':int(formal['baseline']['status']=='bounded_pass' and formal['alternate']['status']=='bounded_pass'),'formal_unbounded_families':0,'physical_families':0})
    summary={'tasks':results,'formal':formal,'counts':counts,'failures':failures}
    (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'counts':counts,'failures':failures},indent=2))
    if failures: raise SystemExit(1)
if __name__=='__main__':main()
