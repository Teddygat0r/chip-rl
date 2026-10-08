"""Separate two-clock validator. Existing single-clock validation is untouched."""
from pathlib import Path
import json,re,shutil,fcntl,tempfile,os
from dataclasses import asdict
from ..evaluate import TrustedEvaluator,sanitize,digest,run,tool,Rejected
from .spec import identity

def inspect(module,c,choice):
 ports=module['ports'];expected={'wclk':('input',1),'rclk':('input',1),'wrst':('input',1),'rrst':('input',1),'w_valid':('input',1),'w_ready':('output',1),'w_data':('input',c.width),'r_valid':('output',1),'r_ready':('input',1),'r_data':('output',c.width)}
 if {k:(v['direction'],len(v['bits'])) for k,v in ports.items()}!=expected:raise Rejected('CDC interface mismatch')
 clocks={ports['wclk']['bits'][0]:'w',ports['rclk']['bits'][0]:'r'};resets={d:ports[d+'rst']['bits'] for d in ('w','r')}
 domains={x:set() for x in ('0','1','x','z')};levels={x:0 for x in domains};ff={};comb=[];consumers={};owner={}
 for name,p in ports.items():
  if p['direction']=='input':
   for b in p['bits']:domains[b]={name[0]};levels[b]=0
 for name,cell in module['cells'].items():
  typ=cell['type'];connections=cell['connections']
  for port,direction in cell['port_directions'].items():
   if direction=='input':
    for b in connections[port]:
     consumers.setdefault(b,[]).append((name,port))
     if b in clocks and port!='C':raise Rejected('clock used as data/gated clock')
  if 'LATCH' in typ.upper():raise Rejected('CDC latch forbidden')
  if 'DFF' in typ:
   if not re.match(r'^\$_(?:DFF_P|DFFE_P[PN]|SDFF_P[PN][01]|SDFF(?:E|CE)_P[PN][01][PN])_$',typ):raise Rejected('CDC positive synchronous FF contract')
   clock=connections.get('C');side=clocks.get(clock[0]) if clock and len(clock)==1 else None
   if side is None:raise Rejected('unknown CDC clock')
   if 'R' in connections and connections['R']!=resets[side]:raise Rejected('foreign reset domain')
   owner[name]=side
   for b in connections['Q']:ff[b]=(name,cell);domains[b]={side};levels[b]=0
  else:comb.append((name,cell))
 while comb:
  later=[]
  for name,cell in comb:
   ins=[b for p,d in cell['port_directions'].items() if d=='input' for b in cell['connections'][p]]
   if not all(b in domains for b in ins):later.append((name,cell));continue
   ds=set().union(*(domains[b] for b in ins));depth=1+max((levels[b] for b in ins),default=0)
   for p,d in cell['port_directions'].items():
    if d=='output':
     for b in cell['connections'][p]:domains[b]=ds;levels[b]=depth
  if len(later)==len(comb):raise Rejected('CDC combinational cycle/undriven net')
  comb=later
 def bits(name):
  net=module['netnames'].get(name)
  if net is None or len(net['bits'])!=c.depth.bit_length():raise Rejected('missing protected CDC role: '+name)
  return net['bits']
 first_stage=set();sync_cells=[]
 for side,remote in [('w','rgray'),('r','wgray')]:
  remote_bits=bits(remote)
  for b in remote_bits:
   if b not in ff or owner[ff[b][0]]==side:raise Rejected('Gray source must be peer-domain registered')
  previous=remote_bits
  for stage in range(1,choice.sync_stages+1):
   current=bits(f'{side}_seen{stage}')
   for b,source in zip(current,previous):
    if b not in ff:raise Rejected('synchronizer stage removed')
    name,cell=ff[b]
    if cell['type']!='$_SDFF_PP0_' or owner[name]!=side or cell['connections']['D']!=[source] or cell['connections']['R']!=resets[side]:raise Rejected('synchronizer must be unconditional local-reset FF chain')
    sync_cells.append(name)
    if stage==1:first_stage.add(name)
   if stage>1:
    for b,next_b in zip(previous,current):
     if consumers.get(b)!=[(ff[next_b][0],'D')]:raise Rejected('intermediate synchronizer tap used')
   previous=current
 for name,cell in module['cells'].items():
  if name not in owner:continue
  for port,direction in cell['port_directions'].items():
   if direction!='input' or port=='C':continue
   if name in first_stage and port=='D':continue
   if any(domains[b]-{owner[name]} for b in cell['connections'][port]):raise Rejected('unprotected cross-domain sequential path')
 for p,side in [('w_ready','w'),('r_valid','r')]:
  if any(domains[b]-{side} for b in ports[p]['bits']):raise Rejected('unprotected cross-domain handshake')
 for p in ('w_ready','r_valid','r_data'):
  if any(b in clocks for b in ports[p]['bits']):raise Rejected('clock output as data')
 area=len(module['cells']);depth=max(levels.values())
 if not 1<=area<=c.max_cells or depth>64:raise Rejected('CDC area/depth budget')
 return {'cells':area,'logic_depth':depth,'synchronizer_flops':len(sync_cells),'clock_domains':2,'structural_policy':'protected Gray sources and untapped2/3-stage chains; no analog safety inference'}

class Synthesis:
 def __init__(self,cache=None):
  self.host=TrustedEvaluator(cache);self.root=self.host.root
 def compile(self,c,choice,source):
  sanitize(source);key=digest(source+identity(c)+json.dumps(asdict(choice),sort_keys=True)+self.host.tool_fingerprint+'cdc-synthesis-v11')
  dest=self.root/('cdc-'+key)
  with (self.root/('cdc-'+key+'.lock')).open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX)
   if not (dest/'netlist.json').exists():
    with tempfile.TemporaryDirectory(dir=self.root,prefix='cdc-build-') as td:
     d=Path(td);(d/'candidate.sv').write_text(source);(d/'synth.ys').write_text(f'read_verilog -sv candidate.sv; chparam -set WIDTH {c.width} -set DEPTH {c.depth} candidate; hierarchy -check -top candidate; synth -top candidate; check -assert; write_json netlist.json; write_verilog -noattr netlist.v')
     run([tool('yosys'),'-s','synth.ys'],d,'synthesis');inspect(json.loads((d/'netlist.json').read_text())['modules']['candidate'],c,choice)
     if dest.exists():shutil.rmtree(dest)
     shutil.copytree(d,dest)
   metrics=inspect(json.loads((dest/'netlist.json').read_text())['modules']['candidate'],c,choice)
   metrics.update(tool_fingerprint=self.host.tool_fingerprint,source_sha256=digest(source),contract_sha256=identity(c))
   return dest,metrics
