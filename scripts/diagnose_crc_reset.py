"""Trusted reproducible CRC reset/evaluator diagnostics, not proof of reliability."""
import argparse,json,platform,sys,resource
from pathlib import Path
from chip_rl.expansion.env import ExpansionEnv
from chip_rl.expansion.evaluate import Evaluator
from chip_rl.evaluate import TrustedEvaluator
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);a.output.chmod(0o700)
environment={'python':sys.version,'platform':platform.platform(),'tool_fingerprint':TrustedEvaluator(a.cache).tool_fingerprint,'tool_limits':{'cpu_seconds':90,'address_space_bytes':3*1024**3,'file_bytes':64*1024**2,'default_wall_seconds':120,'history_wall_seconds':240},'cgroups':{}}
for name in ('cpu.max','memory.max','pids.max'):
 path=Path('/sys/fs/cgroup')/name
 if path.exists():environment['cgroups'][name]=path.read_text().strip()
(a.output/'environment.json').write_text(json.dumps(environment,indent=2));rows=[]
# Fixed host replay seeds, not the public episode seed. Run seed1 twice exactly.
for i,seed in enumerate((1,(1<<127)+20261007,1)):
 env=ExpansionEnv('crc',cache=a.cache)
 original=env.q.evaluate
 def captured(c,src,**kwargs):return original(c,src,replay_seed=seed,artifacts=a.output/f'case-{i}',**kwargs)
 env.q.evaluate=captured
 try:env.reset(17);error=None
 except RuntimeError as e:error=str(e)
 r=env.last;rows.append({'case':i,'host_replay_seed':seed,'episode_seed':17,'tested_correct':r['tested_correct'],'error':error,'evaluation':r})
 (a.output/'summary.json').write_text(json.dumps({'cases':rows,'historical_failure':'v10 original seed and private tool logs unavailable; original failure remains unproven, not retrospectively explained'},indent=2))
 print(i,seed,r['tested_correct'],r.get('long_history',{}).get('error'),flush=True)
