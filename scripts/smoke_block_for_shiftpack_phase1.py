"""Unscored source/mapped N=1,4,16 smoke for frozen serial_shiftpack RTL."""
import hashlib,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.block_for.rtl import design
from chip_rl.block_for.synthesis import Synthesis
from chip_rl.block_for.workloads import generate
from chip_rl.block_for.exact_check import check
from chip_rl.block_for.simulation import simulate

root=Path(os.environ['CHIP_RL_SHIFTPACK_SMOKE_ROOT']);root.mkdir(parents=True,exist_ok=True)
frozen=json.loads((Path(__file__).resolve().parents[1]/'chip_rl/block_for/frozen_sources.json').read_text())
assert set(frozen)=={'serial','chunked4','serial_shiftpack'}
for arch,expected_hash in frozen.items():
 assert hashlib.sha256(design(arch).encode()).hexdigest()==expected_hash
source=design('serial_shiftpack');synth=Synthesis(root/'cache');rows=[]
for n in (1,4,16):
 start=time.monotonic();work=generate(n,0xF0A+n,'development')
 build,struct=synth.compile(n,source)
 dest=root/f'n{n}';dest.mkdir(exist_ok=False)
 exact=check(n,source,build/'netlist.v',work,dest/'exact')
 metric=simulate(n,source,build/'netlist.v',work,dest/'simulation')
 row={'architecture':'serial_shiftpack','N':n,'source_sha256':frozen['serial_shiftpack'],
      'exact_vectors':exact['exact_vectors_checked'],'cells':struct['cells'],
      'logic_depth':struct['logic_depth'],'workload_cycles':metric['workload_cycles'],
      'stream_ii':metric['stream_ii_numerator']/metric['stream_ii_denominator'],
      'long_stall_seen':metric['long_stall_output_seen'],'reset_blocked_seen':metric['reset_blocked_output_seen'],
      'seconds':round(time.monotonic()-start,2)}
 rows.append(row);print(json.dumps(row),flush=True)
(root/'phase1-smoke.json').write_text(json.dumps(rows,indent=2)+'\n')
