"""Combinational SAT equivalence of the deployed sparse24 decoder operand paths."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from chip_rl.sparse24.rtl import design
from chip_rl._tools import tool

BASE=Path(__file__).resolve().parents[1]
ORACLE=r'''
function [3:0] dense_mask;
 input [2:0] selector;
 begin
 case(selector)
 3'd0:dense_mask=4'b0011;
 3'd1:dense_mask=4'b0101;
 3'd2:dense_mask=4'b1001;
 3'd3:dense_mask=4'b0110;
 3'd4:dense_mask=4'b1010;
 3'd5:dense_mask=4'b1100;
 default:dense_mask=4'b0000;
 endcase
 end endfunction
function [7:0] dense_activation;
 input [55:0] slot;input second;
 reg [3:0] mask;
 begin
 mask=dense_mask(slot[50:48]);
 if(second)
  dense_activation=mask[3] ? slot[31:24] : mask[2] ? slot[23:16] :
                   mask[1] ? slot[15:8] : mask[0] ? slot[7:0] : 8'd0;
 else
  dense_activation=mask[0] ? slot[7:0] : mask[1] ? slot[15:8] :
                   mask[2] ? slot[23:16] : mask[3] ? slot[31:24] : 8'd0;
 end endfunction
function [7:0] dense_weight;
 input [55:0] slot;input second;
 begin dense_weight=slot >> (second ? 40 : 32);end endfunction
'''

def sha(data):return hashlib.sha256(data if isinstance(data,bytes) else data.encode()).hexdigest()
def unique(pattern,source,label):
 matches=list(re.finditer(pattern,source,re.S))
 if len(matches)!=1:raise ValueError(f'actual {label} extraction expected one match, got {len(matches)}')
 return matches[0]

def extract():
 serial=design('serial');pipeline=design('pipeline')
 function_pattern=r'function signed \[7:0\] selected_activation;.*?endfunction'
 sf=unique(function_pattern,serial,'serial function').group(0)
 pf=unique(function_pattern,pipeline,'pipeline function').group(0)
 if sf!=pf:raise ValueError('serial and pipeline use different deployed decoder functions')
 serial_path=unique(r'activation\s*=\s*(selected_activation\(slot,index\[0\]\));\s*weight\s*=\s*(index\[0\]\s*\?\s*slot\[47:40\]\s*:\s*slot\[39:32\]);',serial,'serial operands')
 serial_guard=unique(r'if\((slot\[50:48\]<6)\)accum<=accum\+\$signed\(activation\)\*\$signed\(weight\);',serial,'serial MAC guard').group(1)
 block=unique(r'for\(j=0;j<G;j=j\+1\)begin\s*if\((in_data\[56\*j\+48\+:3\]<6)\)begin\s*products0\[2\*j\]<\=\$signed\((selected_activation\(in_data\[56\*j\+:56\],1\'b0\))\)\*\$signed\((in_data\[56\*j\+32\+:8\])\);\s*products0\[2\*j\+1\]<\=\$signed\((selected_activation\(in_data\[56\*j\+:56\],1\'b1\))\)\*\$signed\((in_data\[56\*j\+40\+:8\])\);\s*end else begin products0\[2\*j\]<=0;products0\[2\*j\+1\]<=0;end',pipeline,'elastic guarded product operands')
 return {'rtl_file_sha256':sha((BASE/'chip_rl/sparse24/rtl.py').read_bytes()),
  'serial_source_sha256':sha(serial),'pipeline_source_sha256':sha(pipeline),
  'function':sf,'serial_activation':serial_path.group(1),'serial_weight':serial_path.group(2),
  'serial_guard':serial_guard,'pipeline_guard':block.group(1),
  'pipeline_a0':block.group(2),'pipeline_w0':block.group(3),
  'pipeline_a1':block.group(4),'pipeline_w1':block.group(5)}

def harnesses(extracted):
 f=extracted['function']
 serial=f'''module proof_serial(input [55:0] slot,input [4:0] index,output mismatch);
 {f}\n {ORACLE}
 reg signed [7:0] activation,weight;
 always @* begin activation={extracted['serial_activation']};weight={extracted['serial_weight']};end
 wire actual_enable=({extracted['serial_guard']});
 wire expected_enable=(dense_mask(slot[50:48])!=0);
 wire [7:0] expected_activation=dense_activation(slot,index[0]);
 wire [7:0] expected_weight=dense_weight(slot,index[0]);
 assign mismatch=(activation!=expected_activation)||(weight!=expected_weight)||(actual_enable!=expected_enable);
 endmodule\n'''
 pipeline=f'''module proof_pipeline(input [511:0] in_data,output mismatch);
 {f}\n {ORACLE}
 wire [7:0] wrong;genvar j;
 generate for(j=0;j<8;j=j+1)begin:group
  wire [55:0] slot=in_data[56*j+:56];
  wire [7:0] actual_a0={extracted['pipeline_a0']};
  wire [7:0] actual_w0={extracted['pipeline_w0']};
  wire [7:0] actual_a1={extracted['pipeline_a1']};
  wire [7:0] actual_w1={extracted['pipeline_w1']};
  wire actual_enable=({extracted['pipeline_guard']});
  assign wrong[j]=(actual_a0!=dense_activation(slot,1'b0))||
                  (actual_w0!=dense_weight(slot,1'b0))||
                  (actual_a1!=dense_activation(slot,1'b1))||
                  (actual_w1!=dense_weight(slot,1'b1))||
                  (actual_enable!=(dense_mask(slot[50:48])!=0));
 end endgenerate
 assign mismatch=|wrong;
 endmodule\n'''
 old="3'd1:selected_activation=second ? slot[23:16] : slot[7:0];"
 bad="3'd1:selected_activation=second ? slot[31:24] : slot[7:0];"
 if f.count(old)!=1:raise ValueError('selector-one mutation target changed')
 mutant=serial.replace(f,f.replace(old,bad),1)
 return {'serial':serial,'pipeline':pipeline,'mutant':mutant}

def classify(returncode,log,has_vcd):
 if returncode==0 and 'SAT proof finished - no model found: SUCCESS!' in log and 'proof did fail' not in log:
  return 'proved'
 if returncode!=0 and has_vcd and ('SAT proof finished - model found: FAIL!' in log or 'ERROR: Called with -verify and proof did fail!' in log):
  return 'counterexample'
 return 'unproven_error'

def witness_example(vcd):
 text=Path(vcd).read_text()
 slot=int(re.search(r'b([01]{56}) v2',text).group(1),2)
 index=int(re.search(r'b([01]{5}) v0',text).group(1),2)
 signed=lambda x:x-256 if x>=128 else x
 activations=[signed((slot>>(8*i))&255) for i in range(4)]
 weights=[signed((slot>>(32+8*i))&255) for i in range(2)]
 return {'selector':(slot>>48)&7,'index':index,'second_weight_position':bool(index&1),
         'activations':activations,'weights':weights,
         'dense_expected_selected_activation':activations[2],
         'mutant_selected_activation':activations[3]}

def run_proof(name,source,root,yosys):
 path=root/(name+'.sv');path.write_text(source)
 cmd=[yosys,'-Q','-T','-p',f'read_verilog -formal -sv {path.name}; prep -top proof_{"pipeline" if name=="pipeline" else "serial"} -flatten; check -assert; sat -verify -prove mismatch 0 -set-def-inputs -timeout 110 -show-inputs -show-outputs -dump_vcd {name}-counterexample.vcd']
 try:cp=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=120)
 except subprocess.TimeoutExpired as e:
  (root/(name+'.log')).write_text((e.stdout or b'').decode(errors='replace') if isinstance(e.stdout,bytes) else (e.stdout or ''))
  return {'outcome':'unproven_timeout','returncode':None,'command':cmd,'harness_sha256':sha(source)}
 log=cp.stdout+cp.stderr;(root/(name+'.log')).write_text(log)
 outcome=classify(cp.returncode,log,(root/(name+'-counterexample.vcd')).exists())
 return {'outcome':outcome,'returncode':cp.returncode,'command':cmd,'harness_sha256':sha(source),
         'log_sha256':sha(log),'counterexample_vcd_sha256':sha((root/(name+'-counterexample.vcd')).read_bytes()) if (root/(name+'-counterexample.vcd')).exists() else None}

def main():
 p=argparse.ArgumentParser();p.add_argument('--private',type=Path,required=True);p.add_argument('--summary',type=Path,required=True)
 p.add_argument('--reclassify-existing',action='store_true');a=p.parse_args()
 if a.reclassify_existing:
  summary=json.loads(a.summary.read_text());ex=extract();h=harnesses(ex)
  summary['proof_driver_sha256']=sha(Path(__file__).read_bytes())
  for k in ('rtl_file_sha256','serial_source_sha256','pipeline_source_sha256'):
   if summary['source_sha256'][k]!=ex[k]:raise ValueError('source changed since solver invocation')
  for name,result in summary['results'].items():
   if result['harness_sha256']!=sha(h[name]):raise ValueError('harness changed since solver invocation')
   log=(a.private/(name+'.log')).read_text();vcd=a.private/(name+'-counterexample.vcd')
   if result['log_sha256']!=sha(log):raise ValueError('solver log changed')
   if vcd.exists() and result['counterexample_vcd_sha256']!=sha(vcd.read_bytes()):raise ValueError('witness changed')
   result['outcome']=classify(result['returncode'],log,vcd.exists())
  if summary['results']['mutant']['outcome']=='counterexample':
   summary['counterexample_example']=witness_example(a.private/'mutant-counterexample.vcd')
   summary['counterexample_private_path']=str(a.private/'mutant-counterexample.vcd')
  summary['classification_note']='The first driver expected a FAIL! line; Yosys 0.52 -verify instead emitted proof did fail. Existing log/VCD reclassified without a new solver invocation.'
  a.summary.write_text(json.dumps(summary,indent=2)+'\n')
  print({k:v['outcome'] for k,v in summary['results'].items()})
  if [summary['results'][k]['outcome'] for k in ('serial','pipeline','mutant')]!=['proved','proved','counterexample']:
   raise SystemExit('required proof or counterexample remains unproven')
  return
 a.private.mkdir(parents=True,exist_ok=False);a.private.chmod(0o700)
 ex=extract();h=harnesses(ex)
 yosys=tool('yosys');version=subprocess.run([yosys,'-V'],capture_output=True,text=True,check=True).stdout.strip()
 results={}
 for name in ('serial','pipeline','mutant'):
  results[name]=run_proof(name,h[name],a.private,yosys)
  print(name,results[name]['outcome'],flush=True)
  if name!='mutant' and results[name]['outcome']!='proved':break
 summary={'scope':'combinational selected activation, first/second weight operands, and reserved-zero enable only',
  'proof_driver_sha256':sha(Path(__file__).read_bytes()),
  'source_sha256':{k:v for k,v in ex.items() if k.endswith('sha256')},
  'extracted_expression_sha256':{k:sha(v) for k,v in ex.items() if k not in ('rtl_file_sha256','serial_source_sha256','pipeline_source_sha256')},
  'oracle_sha256':sha(ORACLE),'tool':{'name':'Yosys','version':version,'executable_sha256':sha(Path(yosys).read_bytes())},
  'assumptions':['all top-level bits are defined binary values (-set-def-inputs)','no restrictions on selector, activations, weights, other slot bits or index','combinational proof; no -seq or time bound'],
  'coverage':{'serial':'all 8 selectors, arbitrary signed 8-bit activation bit patterns, both index[0] weight positions and all other slot/index bits',
              'pipeline':'all 8 group positions j=0..7, all 8 selectors per position, both weight positions and arbitrary 512-bit command'},
  'proof_invocations':len(results),'cap':{'invocations':4,'wall_seconds_each':120},'results':results,
  'counterexample_private_path':str(a.private/'mutant-counterexample.vcd') if results.get('mutant',{}).get('outcome')=='counterexample' else None,
  'formal_scope':'decoder operands and enable only; not MAC arithmetic, requantization, handshakes, reset, full-candidate equivalence or physical evaluation'}
 a.summary.parent.mkdir(parents=True,exist_ok=True);a.summary.write_text(json.dumps(summary,indent=2)+'\n')
 if results.get('serial',{}).get('outcome')!='proved' or results.get('pipeline',{}).get('outcome')!='proved' or results.get('mutant',{}).get('outcome')!='counterexample':raise SystemExit('required proof or sensitivity control unproven; see private logs')
if __name__=='__main__':main()
