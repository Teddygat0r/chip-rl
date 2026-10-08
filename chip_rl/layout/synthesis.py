import fcntl,json,tempfile,shutil,re
from pathlib import Path
from dataclasses import asdict
from ..evaluate import TrustedEvaluator,sanitize,digest,Rejected,run,tool
from .spec import PORTS,MAX_CELLS,MAX_DEPTH
GATES={'$_AND_','$_OR_','$_XOR_','$_XNOR_','$_NOT_','$_MUX_','$_NAND_','$_NOR_','$_ANDNOT_','$_ORNOT_'}
def inspect(p):
 m=json.loads((Path(p)/'netlist.json').read_text())['modules']['candidate']
 if {k:(v['direction'],len(v['bits'])) for k,v in m['ports'].items()}!=PORTS:raise Rejected('mapper interface')
 depth={b:0 for p in m['ports'].values() if p['direction']=='input' for b in p['bits']};depth.update({'0':0,'1':0})
 pending=[]
 for cell in m['cells'].values():
  if cell['type'] not in GATES:raise Rejected('mapper must be stateless supported combinational gates')
  ins=[b for n,d in cell['port_directions'].items() if d=='input' for b in cell['connections'][n]];outs=[b for n,d in cell['port_directions'].items() if d=='output' for b in cell['connections'][n]];pending.append((ins,outs))
 while pending:
  rest=[]
  for ins,outs in pending:
   if all(b in depth for b in ins):
    level=1+max((depth[b] for b in ins),default=0)
    for b in outs:depth[b]=level
   else:rest.append((ins,outs))
  if len(rest)==len(pending):raise Rejected('unknown/undriven/cyclic mapper')
  pending=rest
 if any(b not in depth for b in m['ports']['addr']['bits']):raise Rejected('undriven mapper output')
 cells=len(m['cells']);levels=max(depth.values(),default=0)
 if cells>MAX_CELLS or levels>MAX_DEPTH:raise Rejected('mapper resource budget')
 return {'cells':cells,'logic_depth':levels,'state_bits':0}
def source_gate(source):
 # Normalize only a Verilog wildcard event control before the shared attribute ban.
 # Attributes, strings, directives and all other original source remain checked.
 checked=re.sub(r'@\s*\(\s*\*\s*\)', '@*', source) if isinstance(source,str) else source
 sanitize(checked)
 clean=re.sub(r'/\*.*?\*/|//[^\n]*',' ',source,flags=re.S)
 if '.' in clean:raise Rejected('hierarchical access forbidden')
 # Manual sensitivity lists can simulate stale values despite combinational synthesis.
 if re.search(r'\b(always_ff|always_latch)\b',clean):raise Rejected('stateless mapper required')
 for match in re.finditer(r'\balways\b',clean):
  if not re.match(r'\s*@\s*(?:\*|\(\s*\*\s*\))',clean[match.end():]):raise Rejected('automatic combinational sensitivity required')
class Synthesis:
 def __init__(self,cache=None):self.host=TrustedEvaluator(cache);self.root=self.host.root
 def compile(self,shape,source):
  source_gate(source)
  recipe=Path(__file__).read_text();key=digest(source+json.dumps(asdict(shape),sort_keys=True)+self.host.tool_fingerprint+recipe);dest=self.root/('layout-'+key)
  with (self.root/('layout-'+key+'.lock')).open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   if not (dest/'netlist.json').exists():
    with tempfile.TemporaryDirectory(dir=self.root,prefix='layout-build-') as td:
     p=Path(td);(p/'candidate.sv').write_text(source);(p/'synth.ys').write_text(f'read_verilog -sv candidate.sv; chparam -set ROWS {shape.rows} -set COLS {shape.cols} -set BANKS {shape.banks} candidate; hierarchy -check -top candidate; synth -top candidate; check -assert; write_json netlist.json; write_verilog -noattr netlist.v')
     run([tool('yosys'),'-s','synth.ys'],p,'layout-synthesis',30);inspect(p)
     if dest.exists():shutil.rmtree(dest)
     shutil.copytree(p,dest)
   return dest,inspect(dest)
