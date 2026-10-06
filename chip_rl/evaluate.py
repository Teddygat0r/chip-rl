"""Fail-closed local HDL evaluation. Candidate action is source text, never a command."""
import signal
import dataclasses, hashlib, json, math, os, re, resource, shutil, subprocess, tempfile, time
from pathlib import Path
from .tasks import Config, Model, workload, useful_work
from .heldout import challenge

ROOT=Path(__file__).resolve().parents[1]
TOOLS=Path(os.environ.get('CHIP_RL_TOOLS','/workspace/tools/root/usr'))
class Rejected(Exception): pass

def tool(name):
    p=shutil.which(name)
    if p: return p
    p=TOOLS/'bin'/name
    if p.exists(): return str(p)
    raise Rejected('missing required tool: '+name)

def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(90,90))
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def run(cmd, cwd, label, timeout=120):
    log=Path(cwd)/(label+'.log')
    with log.open('w') as f:
        p=subprocess.Popen(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,
                           env={'PATH':str(TOOLS/'bin')+':/usr/bin:/bin','HOME':str(cwd),'LANG':'C'},
                           preexec_fn=limits,start_new_session=True)
        try: p.wait(timeout=timeout)
        except subprocess.TimeoutExpired as e:
            os.killpg(p.pid,signal.SIGKILL);p.wait()
            raise Rejected(label+': timeout') from e
    text=log.read_text()
    if p.returncode: raise Rejected(label+': exit '+str(p.returncode)+'; '+text[-600:])
    return text

def sanitize(src):
    if not isinstance(src,str) or len(src.encode())>100000: raise Rejected('candidate size/type')
    # Comments cannot conceal synthesis pragmas or preprocessor directives.
    if re.search(r'translate[_ ]|synthesis\s+(off|on)|`|\(\*',src,re.I): raise Rejected('directives/attributes forbidden')
    clean=re.sub(r'/\*.*?\*/|//[^\n]*',' ',src,flags=re.S)
    if re.search(r'\b(?:tb|dut)\s*\.',clean): raise Rejected('testbench hierarchy access forbidden')
    if '"' in clean or re.search(r'[#\\]|\b(initial|final|force|release|fork|join|specify|real|shortreal|time|tri|tran|defparam|bind|import|export|package|program|primitive|config|library|disable)\b',clean):
        raise Rejected('non-synthesizable or unsafe construct')
    if any(t not in ('signed','unsigned','clog2') for t in re.findall(r'\$(\w+)',clean)):
        raise Rejected('system task/function forbidden')
    if re.findall(r'\bmodule\s+(\w+)',clean)!=['candidate']: raise Rejected('exactly one candidate module required')

def bench(xs, ys, seed, max_cycles):
    # No hidden stimulus or expected results are compiled into candidate source.
    return f'''module tb;
    reg clk=0,rst=1,in_valid=0,out_ready=0;
    reg [511:0] in_data=0;
    wire in_ready,out_valid; wire [255:0] out_data;
    candidate dut(.*);
    reg [511:0] inputs[0:{len(xs)-1}]; reg [255:0] expected[0:{len(xs)-1}];
    integer weights[0:{len(xs)-1}];
    integer useful=0,useful_latency=0;
    integer accepted[0:{len(xs)-1}];
    integer sent=0,received=0,cycle=0,total_latency=0,j;
    reg [31:0] rng={seed or 1}; reg stalled=0; reg [255:0] held;
    initial begin
      $readmemh("weights.hex",weights); $readmemh("inputs.hex",inputs); $readmemh("expected.hex",expected);
      repeat(3) begin #5;clk=1;#5;clk=0;end
      // Populate the pipeline, then reset with work in flight. All task state must clear.
      rst=0;in_valid=1;in_data=inputs[0];out_ready=0;
      repeat(2) begin #5;clk=1;#5;clk=0;end
      rst=1;in_valid=0;
      repeat(3) begin #5;clk=1;#5;clk=0;end
      rst=0;
      while(received<{len(xs)} && cycle<{max_cycles}) begin
        rng=(rng ^ (rng<<13));rng=(rng ^ (rng>>17));rng=(rng ^ (rng<<5));
        if(!in_valid && sent<{len(xs)}) in_valid=(rng[2:0]!=0);
        if(sent<{len(xs)}) in_data=inputs[sent];
        out_ready=(cycle%71>=18 && rng[5:3]!=0);
        #4;
        if(in_ready!==0 && in_ready!==1) $fatal(1,"unknown ready");
        if(out_valid!==0 && out_valid!==1) $fatal(1,"unknown valid");
        if(stalled && (out_valid!==1 || out_data!==held)) $fatal(1,"unstable stalled output");
        stalled=out_valid && !out_ready; held=out_data;
        if(in_valid && in_ready) begin accepted[sent]=cycle;sent=sent+1;end
        if(out_valid && out_ready) begin
          if(received>=sent) $fatal(1,"unsolicited output");
          if(out_data!==expected[received]) begin
            $display("Mismatch index=%0d expected=%h actual=%h",received,expected[received],out_data);
            $fatal(1,"functional mismatch");
          end
          total_latency=total_latency+cycle-accepted[received];
          useful=useful+weights[received];useful_latency=useful_latency+weights[received]*(cycle-accepted[received]);received=received+1;
        end
        #1;clk=1;#5;clk=0;
        // Ready may change after the edge, so use the recorded accepted count.
        if(sent>0 && accepted[sent-1]==cycle) in_valid=0;
        cycle=cycle+1;
      end
      if(received!={len(xs)} || sent!={len(xs)}) $fatal(1,"dropped work/deadline");
      in_valid=0;out_ready=1;
      repeat(64) begin #4;if(out_valid!==0) $fatal(1,"extra output");#1;clk=1;#5;clk=0;end
      $display("PASS %0d %0d %0d %0d %0d",received,cycle,total_latency,useful,useful_latency);$finish;
    end
    endmodule'''

def simulate(d, source, label):
    cmd=[tool('iverilog')]
    if str(TOOLS) in cmd[0]: cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
    run(cmd+['-g2012','-s','tb','-o',label+'.vvp',source,'tb.sv'],d,label+'-compile')
    text=run([tool('vvp'),label+'.vvp'],d,label+'-simulation',30)
    m=re.search(r'^PASS (\d+) (\d+) (\d+) (\d+) (\d+)$',text,re.M)
    if not m: raise Rejected(label+': no complete result')
    count,cycles,latency,useful,useful_latency=map(int,m.groups())
    return {'transactions':count,'cycles':cycles,'latency_sum':latency,'mean_latency':latency/count,'throughput':count/cycles,'useful_work':useful,'useful_throughput':useful/cycles,'useful_mean_latency':useful_latency/max(1,useful)}

def evaluate(c,source,seed=1,split='train',count=100,artifacts=None,baseline=None):
    start=time.monotonic(); result={'config':dataclasses.asdict(c),'seed':seed,'split':split,'workload_count':count,'correct':False,'reward':0.0,
        'functional':'not_run','synthesis':'not_run','netlist':'not_run','formal':'not_run','physical':'not_run',
        'source_sha256':hashlib.sha256(source.encode()).hexdigest() if isinstance(source,str) else None}
    temp=tempfile.TemporaryDirectory(prefix='chip-rl-'); d=Path(temp.name)
    try:
        if type(seed) is not int or not 0<=seed<=0xffffffff: raise Rejected('seed must be an unsigned 32-bit integer')
        if type(count) is not int or not 1<=count<=4096: raise Rejected('count must be an integer in 1..4096')
        sanitize(source)
        (d/'candidate.sv').write_text(source)
        if split not in ('train','heldout','challenge'): raise Rejected('unknown workload split')
        xs=challenge(c,seed,count) if split=='challenge' else workload(c,seed,count,split); model=Model(c); ys=[model.step(x) for x in xs]
        (d/'inputs.hex').write_text(''.join(f'{x:0128x}\n' for x in xs))
        (d/'weights.hex').write_text(''.join(f'{useful_work(c,x,y):08x}\n' for x,y in zip(xs,ys)))
        result['workload_sha256']=hashlib.sha256((d/'inputs.hex').read_bytes()).hexdigest()
        (d/'expected.hex').write_text(''.join(f'{x:064x}\n' for x in ys))
        (d/'tb.sv').write_text(bench(xs,ys,seed,c.max_cycles))
        result['metrics']=simulate(d,'candidate.sv','rtl');result['functional']='pass'
        script='read_verilog -sv candidate.sv; hierarchy -check -top candidate; synth -top candidate; check -assert; stat; write_json netlist.json; write_verilog -noattr netlist.v'
        (d/'synth.ys').write_text(script)
        run([tool('yosys'),'-s','synth.ys'],d,'synthesis')
        net=json.loads((d/'netlist.json').read_text());mod=net['modules']['candidate'];cells=mod.get('cells',{})
        if any('LATCH' in q['type'].upper() for q in cells.values()): raise Rejected('latches forbidden')
        ports={k:(v['direction'],len(v['bits'])) for k,v in mod['ports'].items()}
        expected={'clk':('input',1),'rst':('input',1),'in_valid':('input',1),'in_ready':('output',1),'in_data':('input',512),'out_valid':('output',1),'out_ready':('input',1),'out_data':('output',256)}
        if ports!=expected: raise Rejected('changed interface')
        result['cells']=len(cells);result['synthesis']='pass'
        if len(cells)>c.max_cells: raise Rejected('area resource budget')
        mapped=simulate(d,'netlist.v','netlist')
        if mapped!=result['metrics']: raise Rejected('simulation/synthesis divergence')
        result['netlist']='pass';result['correct']=True
        result['reward']=1.0
        if baseline is not None:
            if not baseline.get('correct') or baseline['config']!=result['config'] or baseline['seed']!=seed or baseline['split']!=split or baseline.get('workload_sha256')!=result['workload_sha256']:
                raise Rejected('baseline contract mismatch')
            area=baseline['cells']/max(1,result['cells']);speed=baseline['metrics']['useful_mean_latency']/max(0.001,result['metrics']['useful_mean_latency'])
            rate=result['metrics']['useful_throughput']/baseline['metrics']['useful_throughput']
            result['reward']=1+0.2*math.tanh(math.log(area))+0.2*math.tanh(math.log(speed))+0.1*math.tanh(math.log(rate))
    except (Rejected,OSError,ValueError,KeyError) as e:
        result['correct']=False;result['reward']=0.;result['error']=str(e)
    finally:
        result['elapsed_s']=round(time.monotonic()-start,3)
        (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if artifacts:
            dest=Path(artifacts)
            if dest.exists(): raise FileExistsError('artifact destination exists: '+str(dest))
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(d,dest)
        temp.cleanup()
    return result
