"""Read-only installed-prerequisite assessment; does not install or run a flow."""
import argparse,json,shutil,hashlib
from pathlib import Path
from chip_rl.quality.spec import Config
from chip_rl.quality.rtl import design
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
paths=[Path(x) for x in a.inventory.read_text().splitlines()];bins={n:shutil.which(n) for n in ('openroad','sta','opensta','sby','eqy','yosys-smtbmc','z3','boolector','verilator')}
for n in bins:
 if bins[n] is None:
  q=Path('/workspace/tools/root/usr/bin')/n
  if q.is_file():bins[n]=str(q)
libs=[str(p) for p in paths if p.suffix in ('.lib','.lef')];source=design(Config('dot'),'shiftadaptive');(a.output/'candidate.sv').write_text(source)
(a.output/'target.sdc').write_text('# Prospective target only; no routed/timing result.\ncreate_clock -name clk -period 10.0 [get_ports clk]\n')
r={'status':'blocked_missing_prerequisites','physical_verified':False,'physical_metrics':None,'candidate':'dot/shiftadaptive','parameters':{'M':1,'N':1,'K':13},'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'executables':bins,'library_inventory':libs,'flow_root':None,'blockers':['No installed OpenROAD or STA executable found in PATH or inventoried locations','No ORFS flow/platform, technology/cell LEF or compatible ASIC timing library found; Yosys cells.lib is a generic FF mapping library, not a physical PDK'],'network_used':False,'installed_software':False,'target_clock_ns':10,'target_is_achieved':False,'next_requirement':'A trusted preinstalled physical flow plus licensed/usable PDK and timing corners; then qualify placement/routing, STA and DRC before any physical PPA claim.'}
(a.output/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
