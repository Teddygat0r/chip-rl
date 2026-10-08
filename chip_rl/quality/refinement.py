"""Bounded-cost concrete/abstract transition refinement, trusted-host only."""
import copy,json,re,time
from pathlib import Path
from ..evaluate import run,tool,Rejected,digest
from .induction import model
from .spec import Config

def extract(source,c,root,kind,*,negative=None):
 if kind not in ('original','concrete','abstract'):raise ValueError('kind')
 if (c.k,c.m,c.n)!=(16,1,1):raise ValueError('fixed K16 single-output scope')
 root=Path(root);root.mkdir(parents=True,exist_ok=False)
 if kind=='original':
  src=source;h='''module formal_top(input clk,reset_in,in_valid,out_ready,input [1023:0] in_data,output in_ready,out_valid,output [383:0] out_data);
 reg started=0;always @(posedge clk)started<=1;wire rst=!started || reset_in;
 candidate #(.M(1),.N(1),.K(16)) dut(.*);endmodule'''
 else:src,h,_=model(source,c,concrete=kind=='concrete')
 if negative:
  changes={'product_capture':('proof_saved<=proof_real_tokens','proof_saved<=proof_real_tokens ^ 256\'b1'),'operand_capture':('qa[8*q+:8]<=in_data[8*(16*r+q)+:8]','qa[8*q+:8]<=in_data[8*(16*r+q)+:8] ^ 8\'b1')}
  if kind!='concrete' or negative not in changes:raise ValueError('negative control')
  old,new=changes[negative]
  if src.count(old)!=1:raise ValueError('mutation anchor')
  src=src.replace(old,new)
 (root/'candidate.sv').write_text(src);(root/'formal.sv').write_text(h)
 script='read_verilog -formal -sv candidate.sv formal.sv; hierarchy -check -top formal_top; proc; flatten; memory_map; opt -nodffe -nosdff; chformal -lower; check -assert; write_json raw.json'
 (root/'extract.ys').write_text(script);run([tool('yosys'),'-s','extract.ys'],root,'extract',35)
 raw=json.loads((root/'raw.json').read_text());m=copy.deepcopy(raw['modules']['formal_top']);q_to_d={};removed=[]
 for name,cell in list(m['cells'].items()):
  t=cell['type']
  if t=='$dff':
   if int(cell['parameters']['CLK_POLARITY'],2)!=1 or cell['connections']['CLK']!=m['ports']['clk']['bits']:raise ValueError('clock contract')
   if len(cell['connections']['Q'])!=len(cell['connections']['D']):raise ValueError('D/Q width')
   for q,d in zip(cell['connections']['Q'],cell['connections']['D']):
    if not isinstance(q,int) or q in q_to_d:raise ValueError('nonunique state driver')
    q_to_d[q]=d
   del m['cells'][name]
  elif t in ('$assume','$assert','$cover'):
   removed.append(t);del m['cells'][name]
  elif re.search(r'ff|latch|mem|check',t,re.I):raise ValueError('unsupported state/formal cell: '+t)
 qbits=sorted(q_to_d);index={b:i for i,b in enumerate(qbits)};aliases={}
 for name,n in m['netnames'].items():
  n.get('attributes',{}).pop('init',None)
  if not n.get('hide_name',0):
   for i,b in enumerate(n['bits']):
    if b in index:aliases[f'{name}:{i}']=index[b]
 ports={name:port for name,port in m['ports'].items() if port['direction']=='input'}
 ports['state']={'direction':'input','bits':qbits};ports['next_state']={'direction':'output','bits':[q_to_d[b] for b in qbits]}
 for name,net in [('ready','in_ready'),('valid','out_valid'),('data','out_data')]:ports[name]={'direction':'output','bits':m['netnames'][net]['bits']}
 m['ports']=ports;m['attributes']={};module='transition_'+kind
 tree={'creator':'chip-rl source-bound D/Q extraction','modules':{module:m}}
 (root/'transition.json').write_text(json.dumps(tree))
 metadata={'kind':kind,'negative_control':negative,'source_sha256':digest(source),'model_sha256':digest(src),'harness_sha256':digest(h),'config':vars(c),'module':module,'state_bits':len(qbits),'aliases':aliases,'ports':{n:len(p['bits']) for n,p in ports.items()},'removed_formal_cells':removed,'dff_only_extraction':True,'transition_sha256':digest((root/'transition.json').read_text())}
 (root/'metadata.json').write_text(json.dumps(metadata,indent=2));return metadata

def union_states(metas):
 parent={};aliases={}
 def find(x):
  parent.setdefault(x,x)
  if parent[x]!=x:parent[x]=find(parent[x])
  return parent[x]
 def join(a,b):parent[find(b)]=find(a)
 for m in metas:
  kind=m['kind']
  for i in range(m['state_bits']):find((kind,i))
  for a,i in m['aliases'].items():
   if a in aliases:join((kind,i),aliases[a])
   else:aliases[a]=(kind,i)
 groups={};mapping={}
 for node in parent:
  root=find(node);groups.setdefault(root,len(groups));mapping[node]=groups[root]
 # Reject name aliasing that merges distinct live bits in the same model.
 for m in metas:
  xs=[mapping[(m['kind'],i)] for i in range(m['state_bits'])]
  if len(xs)!=len(set(xs)):raise ValueError('inconsistent state aliases')
 return mapping,{a:mapping[n] for a,n in aliases.items()},len(groups)

def wrapper(roots,mode,case=None):
 roots=[Path(p) for p in roots];metas=[json.loads((p/'metadata.json').read_text()) for p in roots]
 if len({(m['source_sha256'],json.dumps(m['config'],sort_keys=True)) for m in metas})!=1:raise ValueError('source/config mismatch')
 mapping,aliases,count=union_states(metas);bindings={};lines=[]
 def bind(name,width,expression):
  for i in range(width):
   a=f'{name}:{i}'
   if a in aliases:
    key=aliases[a];v=f'{expression}[{i}]'
    if key in bindings and bindings[key]!=v:raise ValueError('conflicting mapping')
    bindings[key]=v
 def const(name,width,value):
  for i in range(width):
   if f'{name}:{i}' in aliases:bindings[aliases[f'{name}:{i}']]=f"1'b{(value>>i)&1}"
 # Product function is concrete and fully signed. Snapshot is an arbitrary1024-bit input.
 lines+=['wire [255:0] products,incoming;wire [127:0] qa_map,qb_map;']
 for j in range(16):
  lines+=[f'wire signed [7:0] a{j}=snapshot[{8*j}+:8],b{j}=snapshot[{512+32*j}+:8],ia{j}=in_data[{8*j}+:8],ib{j}=in_data[{512+32*j}+:8];',f'wire signed [15:0] p{j}=a{j}*b{j},ip{j}=ia{j}*ib{j};assign products[{16*j}+:16]=p{j};assign incoming[{16*j}+:16]=ip{j};']
 if mode=='equivalence':
  if case not in range(7):raise ValueError('case')
  const('started',1,case!=0);const('dut.proof_started',1,case!=0)
  if case:
   bind('dut.proof_input',1024,'snapshot');bind('dut.command',1024,'snapshot');bind('dut.proof_saved',256,'products')
   const('dut.busy',1,case>=3);const('dut.ov',1,case==2)
   if case>=3:
    pos=4*(case-3);const('dut.pos',32,pos)
    lines+=[f'assign qa_map=snapshot[127:0]>>{8*pos};']
    for j in range(16):lines+=[f'assign qb_map[{8*j}+:8]='+ (f'snapshot[{512+32*(pos+j)}+:8];' if pos+j<16 else "8'b0;")]
    bind('dut.R[0].C[0].qa',128,'qa_map');bind('dut.R[0].C[0].qb',128,'qb_map')
 elif mode=='capture':
  if case not in range(5):raise ValueError('capture case')
  if case!=0:
   const('started',1,1);const('dut.proof_started',1,1)
   bind('dut.proof_input',1024,'snapshot');bind('dut.proof_saved',256,'products')
  if case==1:const('dut.busy',1,0);const('dut.ov',1,0)
  if case==3:const('dut.busy',1,1);const('dut.ov',1,0)
  if case==4:const('dut.busy',1,0);const('dut.ov',1,1)
 elif mode!='noninterference':raise ValueError('mode')
 for m in metas:
  kind=m['kind'];n=m['state_bits'];lines+=[f'wire [{n-1}:0] state_{kind},next_{kind};wire ready_{kind},valid_{kind};wire [383:0] data_{kind};']
  for i in range(n):lines+=[f'assign state_{kind}[{i}]={bindings.get(mapping[(kind,i)],"free_state["+str(mapping[(kind,i)])+"]")};']
  rst='reset_in';valid='in_valid'
  if mode=='capture':
   rst='reset_in' if case==0 else "1'b0"
   if case==1:valid="1'b1"
   if case==2:valid="1'b0"
  args=f'.clk(clk),.reset_in({rst}),.in_valid({valid}),.out_ready(out_ready),.in_data(in_data),.state(state_{kind}),.next_state(next_{kind}),.ready(ready_{kind}),.valid(valid_{kind}),.data(data_{kind})'
  if 'proof_tokens' in m['ports']:args+=',.proof_tokens(incoming)'
  lines+=[f'{m["module"]} {kind}({args});']
 if mode=='capture':
  m=metas[0];kind=m['kind'];a=m['aliases'];terms=[]
  def nxt(name,lo,width):
   bits=[f'next_{kind}[{a[f"{name}:{i}"]}]' for i in range(lo+width-1,lo-1,-1)]
   return '{'+','.join(bits)+'}'
  for j in range(16):
   aa=nxt('dut.proof_input',8*j,8);bb=nxt('dut.proof_input',512+32*j,8);pp=nxt('dut.proof_saved',16*j,16)
   lines+=[f'wire signed [7:0] na{j}={aa},nb{j}={bb};wire signed [15:0] np{j}=na{j}*nb{j};']
   terms.append(f'({pp}==np{j})')
  predicate=' && '.join(terms)
  if case==0:
   start_index=aliases['started:0']
   predicate=f'(!(!free_state[{start_index}] || reset_in)) || ('+predicate+')'
 else:
  left,right=metas;k1,k2=left['kind'],right['kind'];a1,a2=left['aliases'],right['aliases'];pairs=set()
  for alias in set(a1)&set(a2):pairs.add((a1[alias],a2[alias]))
  if len({i for i,j in pairs})!=left['state_bits'] or (mode=='equivalence' and len({j for i,j in pairs})!=right['state_bits']):raise ValueError('unmapped state bits')
  predicate=' && '.join([f'(next_{k1}[{i}]==next_{k2}[{j}])' for i,j in sorted(pairs)]+[f'(ready_{k1}==ready_{k2})',f'(valid_{k1}==valid_{k2})',f'(!valid_{k1} || data_{k1}==data_{k2})'])
 lines+=['assign refinement_ok='+predicate+';']
 text=f'module formal_top(input clk,reset_in,in_valid,out_ready,input [1023:0] in_data,snapshot,input [{count-1}:0] free_state,output refinement_ok);\n'+'\n'.join(lines)+'\nendmodule\n'
 return text,{'mode':mode,'case':case,'source_sha256':metas[0]['source_sha256'],'config':metas[0]['config'],'models':[{k:m[k] for k in ('kind','model_sha256','transition_sha256','state_bits')} for m in metas],'state_groups':count,'binding_count':len(bindings),'unconditional_reset_establishment':mode=='capture' and case==0,'assumptions':'state substitution from v17 invariant and captured-product relation; no assume cells in SAT miter','concrete_composition_complete':False}

def prove(roots,root,mode,case=None):
 root=Path(root);root.mkdir(parents=True,exist_ok=False);start=time.monotonic();h,meta=wrapper(roots,mode,case)
 (root/'miter.sv').write_text(h)
 reads=[]
 for i,p in enumerate(roots):
  data=(Path(p)/'transition.json').read_text();(root/f'transition-{i}.json').write_text(data);reads.append(f'read_json transition-{i}.json')
 script='; '.join(reads)+ '; read_verilog -formal -sv miter.sv; hierarchy -check -top formal_top; flatten; proc; opt; check -assert; write_json miter.json; sat -prove refinement_ok 1 -verify -timeout 20 -show-ports -dump_json witness.json -dump_vcd witness.vcd'
 (root/'proof.ys').write_text(script);r={'status':'unproven','solver_timeout_s':20,'wall_timeout_s':35,**meta}
 try:
  log=run([tool('yosys'),'-s','proof.ys'],root,'proof',35)
  if 'SAT proof finished - no model found: SUCCESS!' in log:r['status']='combinational_refinement_pass'
 except (Rejected,OSError) as e:
  r['error']=str(e);log=(root/'proof.log').read_text() if (root/'proof.log').exists() else ''
  if 'SAT proof finished - model found: FAIL!' in log:r['status']='counterexample'
 r['elapsed_s']=round(time.monotonic()-start,3);(root/'result.json').write_text(json.dumps(r,indent=2));return r
