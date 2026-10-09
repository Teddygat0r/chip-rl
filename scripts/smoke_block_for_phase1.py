"""Unscored frozen-reference source and mapped smoke for N=1,4,16."""
import hashlib,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.block_for.rtl import design
from chip_rl.block_for.synthesis import Synthesis
from chip_rl.block_for.workloads import generate
from chip_rl.block_for.exact_check import check
from chip_rl.block_for.simulation import simulate
from chip_rl.block_for.oracle import decode_output

root=Path(os.environ.get('CHIP_RL_SMOKE_ROOT','/tmp/chip-rl-block-for-smoke'))
root.mkdir(parents=True,exist_ok=True)
frozen=json.loads((Path(__file__).resolve().parents[1]/'chip_rl/block_for/frozen_sources.json').read_text())
synth=Synthesis(root/'cache')
rows=[]
for arch in ('serial','chunked4'):
 source=design(arch)
 assert hashlib.sha256(source.encode()).hexdigest()==frozen[arch]
 for n in (1,4,16):
  t=time.monotonic();work=generate(n,0xF0A+n,'development')
  build,struct=synth.compile(n,source)
  dest=root/f'{arch}-n{n}';dest.mkdir(exist_ok=True)
  exact=check(n,source,build/'netlist.v',work,dest/'exact')
  metric=simulate(n,source,build/'netlist.v',work,dest/'simulation')
  assert all(decode_output(y,n)==tuple((x>>(8*i))&255 for i in range(n)) for x,y in zip(work['inputs'],work['expected']))
  row={'architecture':arch,'N':n,'source_sha256':frozen[arch], 'exact_vectors':exact['exact_vectors_checked'],
       'cells':struct['cells'],'workload_cycles':metric['workload_cycles'],
       'stream_ii':metric['stream_ii_numerator']/metric['stream_ii_denominator'],
       'long_stall_seen':metric['long_stall_output_seen'],'reset_blocked_seen':metric['reset_blocked_output_seen'],
       'seconds':round(time.monotonic()-t,2)}
  rows.append(row);print(json.dumps(row),flush=True)
(root/'phase1-smoke.json').write_text(json.dumps(rows,indent=2)+'\n')
