"""Copied-source N=4 format/numerical mutation probes; never alters references."""
from pathlib import Path
import hashlib,json,os,re,sys
from chip_rl.block_rle.rtl import design
from chip_rl.block_rle.oracle import pack_input,expected
from chip_rl.block_rle.synthesis import Synthesis
from chip_rl.evaluate import run,tool,TOOLS,Rejected

MUTATIONS={
 'off_by_one_length':("next_length=next_length+1'b1;","next_length=next_length+2'd2;",(65,65,66,67)),
 'merge_nonadjacent_repeat':('next_prior==value','(next_prior==value || value==bytes_reg[7:0])',(65,66,65,67)),
 'nonzero_unused_output':("assign out_data={43'b0,count,payload};","assign out_data={43'b0,count,payload} | (256'd1 << 207);",(0,0,255,0)),
}
TB='''module tb;
reg clk=0,rst=1,in_valid=0,out_ready=1;reg [511:0] in_data=512'hINPUT;
wire in_ready,out_valid;wire [255:0] out_data;
candidate INSTANTIATION dut(.*);
integer t=0;
initial begin
 #2;clk=1;#2;clk=0;rst=0;in_valid=1;
 #2;if(in_ready!==1)$fatal(1,"NO_ACCEPT");clk=1;#2;clk=0;in_valid=0;
 while(out_valid!==1 && t<100)begin #2;clk=1;#2;clk=0;t=t+1;end
 #2;if(out_valid!==1)$fatal(1,"NO_RESPONSE");
 if(out_data!==256'hEXPECTED)$fatal(1,"EXACT_MISMATCH observed=%h expected=%h",out_data,256'hEXPECTED);
 $display("UNDETECTED");$finish;
end endmodule'''

def sources():
 base=design('serial');result={}
 for name,(old,new,values) in MUTATIONS.items():
  if base.count(old)!=1:raise RuntimeError('mutation anchor changed: '+name)
  result[name]={'source':base.replace(old,new),'values':values,'input':pack_input(values),'expected':expected(pack_input(values),4)}
 return result

def freeze(root):
 root=Path(root);root.mkdir(parents=True,exist_ok=True)
 result=sources();manifest={}
 for name,entry in result.items():
  (root/(name+'.sv')).write_text(entry['source'])
  manifest[name]={'source_sha256':hashlib.sha256(entry['source'].encode()).hexdigest(),
   'witness_bytes':entry['values'],'witness_input':f"{entry['input']:0128x}",
   'oracle_output':f"{entry['expected']:064x}"}
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return manifest

def run_probe(root,cache):
 root=Path(root).resolve();manifest=json.loads((root/'manifest.json').read_text());out=[];s=Synthesis(cache)
 for name,entry in sources().items():
  case=manifest[name]
  assert case['source_sha256']==hashlib.sha256(entry['source'].encode()).hexdigest()
  assert case['witness_input']==f"{entry['input']:0128x}" and case['oracle_output']==f"{entry['expected']:064x}"
  build,struct=s.compile(4,entry['source'])
  case_root=root/name;case_root.mkdir(exist_ok=True)
  (case_root/'netlist.v').write_bytes((build/'netlist.v').read_bytes())
  for stage,file in (('rtl',root/(name+'.sv')),('mapped',case_root/'netlist.v')):
   tb=TB.replace('INPUT',case['witness_input']).replace('EXPECTED',case['oracle_output']).replace('INSTANTIATION','#(.N(4))' if stage=='rtl' else '')
   (case_root/(stage+'-tb.sv')).write_text(tb)
   cmd=[tool('iverilog')]
   if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
   run(cmd+['-g2012','-s','tb','-o',stage+'.vvp',str(file),stage+'-tb.sv'],case_root,name+'-'+stage+'-compile',45)
   try:
    run([tool('vvp'),stage+'.vvp'],case_root,name+'-'+stage+'-simulation',90)
   except Rejected as e:
    if 'EXACT_MISMATCH' not in str(e):raise
    out.append({'mutation':name,'stage':stage,'synthesis':'pass','compile':'pass','outcome':'detected_wrong_answer','cells':struct['cells']})
   else:raise RuntimeError('mutant survived: '+name+' '+stage)
 return out

if __name__=='__main__':
 root=Path(sys.argv[1]);cache=Path(sys.argv[2])
 if not (root/'manifest.json').exists():freeze(root)
 print(json.dumps(run_probe(root,cache),indent=2))
