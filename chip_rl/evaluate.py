"""Trusted v2 qualification: fresh private instances, parameter shifts and paired metrics.
Only source text enters from an agent. Replay seeds/artifact paths are host-only.
"""
import fcntl,hashlib,json,math,os,re,secrets,shutil,tempfile,time
from .audit import journal
from pathlib import Path
from dataclasses import replace,asdict
from ._tools import Rejected,tool,run,sanitize as _sanitize,TOOLS
from .tasks import Model,useful_work
from .corpus import commands,schedule,dirty_command
from .contracts import specification,identity,PILOT
from .rtl import design
from .coverage import cases,PROFILE
from .objectives import scores,ratios,relation

def sanitize(source):
    if not isinstance(source,str):return _sanitize(source)
    # Only the module parameter declaration may use #; time delays remain banned.
    checked=re.sub(r'(module\s+candidate\s*)#\s*\(',r'\1(',source,count=1)
    _sanitize(checked)

def digest(text):return hashlib.sha256(text.encode()).hexdigest()

def reward(base,candidate):
    """Monotone area-first objective, with cycle/QoS gates applied beforehand."""
    loss=.8*math.log(candidate['cells']/base['cells'])+.15*math.log(candidate['cycles']/base['cycles'])+.05*math.log((candidate['offered_latency']+1)/(base['offered_latency']+1))
    return 1-.5*math.tanh(loss)

def logical_depth(module):
    depth={b:0 for p in module['ports'].values() if p['direction']=='input' for b in p['bits']};depth.update({'0':0,'1':0,'x':0,'z':0})
    cells=module['cells'];comb=[];clock=module['ports']['clk']['bits'][0]
    for cell in cells.values():
        typ=cell['type'];ins=[b for p,d in cell['port_directions'].items() if d=='input' for b in cell['connections'][p]]
        outs=[b for p,d in cell['port_directions'].items() if d=='output' for b in cell['connections'][p]]
        if 'LATCH' in typ.upper():raise Rejected('latch forbidden')
        if 'DFF' in typ:
            # Generic Yosys FFs: only positive clk, synchronous resets/enables.
            if not re.match(r'^\$_(?:DFF_P|DFFE_P[PN]|SDFF_P[PN][01]|SDFF(?:E|CE)_P[PN][01][PN])_$',typ) or cell['connections'].get('C')!=[clock]:
                raise Rejected('clock contract violation')
            if typ.startswith('$_DFF_') and typ!='$_DFF_P_':raise Rejected('asynchronous reset forbidden')
            depth.update({b:0 for b in outs})
        else:comb.append((ins,outs))
    while comb:
        rest=[];changed=False
        for ins,outs in comb:
            if all(b in depth for b in ins):
                level=1+max((depth[b] for b in ins),default=0)
                depth.update({b:level for b in outs});changed=True
            else:rest.append((ins,outs))
        if not changed:raise Rejected('combinational cycle or undriven net')
        comb=rest
    return max(depth.values(),default=0)

def bench(c,xs,seed):
    arrival,ready,limit=schedule(c,len(xs),seed)
    return f'''module tb;
    reg clk=0,rst=1,in_valid=0,out_ready=0;reg [511:0] in_data=0;
    wire in_ready,out_valid;wire [255:0] out_data;
    candidate #(.WIDTH({c.width}),.DEPTH({c.depth}),.K({c.k})) dut(.*);
    reg [511:0] inputs[0:{len(xs)-1}];reg [255:0] expected[0:{len(xs)-1}];
    integer releases[0:{len(xs)-1}],weights[0:{len(xs)-1}],accepted[0:{len(xs)-1}];
    reg consumers[0:{len(ready)-1}];
    integer sent=0,received=0,cycle=0,units=0,total_latency=0,max_latency=0;
    reg stalled=0;reg [255:0] held=0;
    initial begin
      $readmemh("inputs.hex",inputs);$readmemh("expected.hex",expected);
      $readmemh("release.hex",releases);$readmemh("weights.hex",weights);$readmemh("ready.hex",consumers);
      repeat(3)begin #5;clk=1;#5;clk=0;end
      rst=0;in_valid=1;in_data=512'h{dirty_command(c):x};out_ready=1;
      repeat(4)begin #5;clk=1;#5;clk=0;end
      {"in_data=512'hdeadbeef000002;repeat(8)begin #5;clk=1;#5;clk=0;end" if c.name=='cache' else ''}
      rst=1;in_valid=1;in_data=512'h{'f'*128};repeat(3)begin #5;clk=1;#5;clk=0;end rst=0;
      while(received<{len(xs)} && cycle<{limit})begin
        if(sent<{len(xs)})begin in_valid=(cycle>=releases[sent]);in_data=inputs[sent];end else in_valid=0;
        out_ready=consumers[cycle];#4;
        if(in_ready!==0 && in_ready!==1)$fatal(1,"unknown ready");
        if(out_valid!==0 && out_valid!==1)$fatal(1,"unknown valid");
        if(stalled && (out_valid!==1 || out_data!==held))$fatal(1,"stalled response changed");
        stalled=out_valid && !out_ready;held=out_data;
        if(in_valid && in_ready)begin accepted[sent]=cycle;sent=sent+1;end
        if(out_valid && out_ready)begin
          if(received>=sent)$fatal(1,"unsolicited output");
          if(cycle-accepted[received]<1)$fatal(1,"minimum registered latency");
          if(cycle-accepted[received]>64)$fatal(1,"response deadline");
          if(out_data!==expected[received])$fatal(1,"functional mismatch");
          units=units+weights[received];total_latency=total_latency+weights[received]*(cycle-releases[received]);
          if(cycle-accepted[received]>max_latency)max_latency=cycle-accepted[received];received=received+1;
        end
        {'if(cycle==8 && sent<4)$fatal(1,"minimum storage capacity");' if c.name=='elastic' else ''}
        #1;clk=1;#5;clk=0;cycle=cycle+1;
      end
      if(sent!={len(xs)} || received!={len(xs)})$fatal(1,"completion deadline/dropped work");
      in_valid=0;out_ready=1;
      repeat(80)begin #4;if(out_valid!==0)$fatal(1,"extra output");#1;clk=1;#5;clk=0;end
      $display("PASS %0d %0d %0d %0d %0d",received,cycle,units,total_latency,max_latency);$finish;
    end endmodule''',arrival,ready

class TrustedEvaluator:
    def __init__(self,cache_root=None):
        self._temp=None
        if cache_root is None:
            self._temp=tempfile.TemporaryDirectory(prefix='chip-rl-v2-cache-');cache_root=self._temp.name
        self.recipe_fingerprint=hashlib.sha256(b''.join(Path(__file__).with_name(n).read_bytes() for n in ('evaluate.py','corpus.py','tasks.py','contracts.py','_tools.py','coverage.py','objectives.py'))).hexdigest()
        self.root=Path(cache_root);self.root.mkdir(parents=True,exist_ok=True);self.root.chmod(0o700)
        # Include executable contents, not merely version labels, in cache identity.
        bins=[Path(tool(n)) for n in ('yosys','yosys-abc','iverilog','vvp')]
        self.tool_fingerprint=hashlib.sha256(b''.join(hashlib.sha256(p.read_bytes()).digest() for p in bins)).hexdigest()

    def close(self):
        if self._temp is not None:self._temp.cleanup();self._temp=None
    def __del__(self):
        if getattr(self,'_temp',None) is not None:self.close()

    def _synth(self,c,src):
        sanitize(src)
        lockkey=digest(src+json.dumps(asdict(c),sort_keys=True)+self.tool_fingerprint+identity(c))
        with (self.root/(lockkey+'.lock')).open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            return self._synth_locked(c,src)

    def _synth_locked(self,c,src):
        sanitize(src)
        key=digest(src+json.dumps(asdict(c),sort_keys=True)+self.tool_fingerprint+identity(c));dest=self.root/key
        if (dest/'complete.json').exists():
            cached=json.loads((dest/'complete.json').read_text())
            # Reapply the current structural validator even to a trusted old cache.
            mapped=json.loads((dest/'netlist.json').read_text())['modules']['candidate']
            cached['logic_depth']=logical_depth(mapped)
            if cached['logic_depth']>specification(c)['mapped_logic_depth_limit']:raise Rejected('logic-depth budget')
            return dest,cached,True
        with tempfile.TemporaryDirectory(dir=self.root,prefix='build-') as td:
            d=Path(td);(d/'candidate.sv').write_text(src)
            script=f'read_verilog -sv candidate.sv; chparam -set WIDTH {c.width} -set DEPTH {c.depth} -set K {c.k} candidate; hierarchy -check -top candidate; synth -top candidate; check -assert; write_json netlist.json; write_verilog -noattr netlist.v'
            (d/'synth.ys').write_text(script);run([tool('yosys'),'-s','synth.ys'],d,'synthesis')
            m=json.loads((d/'netlist.json').read_text())['modules']['candidate']
            ports={k:(v['direction'],len(v['bits'])) for k,v in m['ports'].items()}
            want={'clk':('input',1),'rst':('input',1),'in_valid':('input',1),'in_ready':('output',1),'in_data':('input',512),'out_valid':('output',1),'out_ready':('input',1),'out_data':('output',256)}
            if ports!=want:raise Rejected('changed interface')
            area=len(m.get('cells',{}));depth=logical_depth(m)
            if area>c.max_cells or area<1:raise Rejected('cell budget')
            if depth>specification(c)['mapped_logic_depth_limit']:raise Rejected('logic-depth budget')
            metrics={'cells':area,'logic_depth':depth,'tool_fingerprint':self.tool_fingerprint,'source_sha256':digest(src),'contract_sha256':identity(c)}
            (d/'complete.json').write_text(json.dumps(metrics,sort_keys=True)+'\n')
            if dest.exists():shutil.rmtree(dest)
            # Rename a complete build under the per-key lock; incomplete entries never hit.
            shutil.copytree(d,str(d)+'-complete');os.rename(str(d)+'-complete',dest)
        return dest,metrics,False

    def _simulate(self,c,src,synthdir,seed,count,out=None,rtl_only=False):
        xs=commands(c,seed,count);model=Model(c);ys=[model.step(x) for x in xs]
        tb,arrivals,ready=bench(c,xs,seed)
        with tempfile.TemporaryDirectory(prefix='chip-rl-v2-private-') as td:
            d=Path(td);(d/'candidate.sv').write_text(src);(d/'tb.sv').write_text(tb)
            for name,vals,width in [('inputs',xs,128),('expected',ys,64),('release',arrivals,8),('weights',[useful_work(c,x,y) for x,y in zip(xs,ys)],8),('ready',ready,1)]:
                (d/(name+'.hex')).write_text(''.join(f'{v:0{width}x}\n' for v in vals))
            if not rtl_only:shutil.copy(synthdir/'netlist.v',d/'netlist.v')
            answers=[]
            try:
                for label,file in ([('rtl','candidate.sv')] if rtl_only else [('rtl','candidate.sv'),('netlist','netlist.v')]):
                    # Yosys's mapped module has resolved parameters; do not re-override it.
                    if label=='netlist':(d/'tb.sv').write_text(tb.replace(f'candidate #(.WIDTH({c.width}),.DEPTH({c.depth}),.K({c.k}))','candidate'))
                    cmd=[tool('iverilog')]
                    if str(TOOLS) in cmd[0]:cmd+=['-B',str(TOOLS/'lib/x86_64-linux-gnu/ivl')]
                    # Harness constants and exact compiled design identify reusable
                    # simulator programs; private vectors stay runtime-only files.
                    ck=digest(self.tool_fingerprint+(d/file).read_text()+(d/'tb.sv').read_text())
                    cached=self.root/('ivl-'+ck+'.vvp')
                    with (self.root/('ivl-'+ck+'.lock')).open('a') as lock:
                        fcntl.flock(lock,fcntl.LOCK_EX)
                        if cached.exists():shutil.copy(cached,d/(label+'.vvp'))
                        else:
                            run(cmd+['-g2012','-s','tb','-o',label+'.vvp',file,'tb.sv'],d,label+'-compile')
                            shutil.copy(d/(label+'.vvp'),str(cached)+'.new');os.replace(str(cached)+'.new',cached)
                    output=run([tool('vvp'),label+'.vvp'],d,label+'-simulation',120)
                    m=re.search(r'^PASS (\d+) (\d+) (\d+) (\d+) (\d+)$',output,re.M)
                    if not m:raise Rejected('incomplete simulation')
                    answers.append(tuple(map(int,m.groups())))
                if not rtl_only and answers[0]!=answers[1]:raise Rejected('RTL/netlist divergence')
                n,cycles,units,lat,mx=answers[0]
                return {'commands':n,'cycles':cycles,'useful_units':units,'offered_latency':lat/max(1,units),'useful_throughput':units/cycles,'maximum_response_cycles':mx}
            finally:
                if out:
                    target=Path(out);target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(d,target)
                    (target/'private-replay.json').write_text(json.dumps({'config':asdict(c),'seed':seed,'count':count})+'\n')

    @journal
    def evaluate(self,c,src,*,replay_seed=None,count=None,artifacts=None,allow_experimental=False):
        started=time.monotonic();pub={'tested_correct':False,'reward':0.,'family':c.name,'contract':identity(c),'source_sha256':digest(src) if isinstance(src,str) else None,
            'validation':'not_run','formal':'not_run','physical':'not_run','os_isolation':'not_provided','pilot_eligible':c.name in PILOT,'coverage_profile':PROFILE,'objective':c.objective,'objective_eligible':False}
        private=[];cache_hits=0;baseline_hits=0
        try:
            if c.name not in PILOT and not allow_experimental:raise Rejected('experimental family excluded from pilot')
            if replay_seed is not None and (type(replay_seed) is not int or not 0<=replay_seed<2**128):raise Rejected('invalid trusted replay seed')
            seed=secrets.randbits(128) if replay_seed is None else replay_seed
            plan=cases(c,seed,count)
            sanitize(src)
            # Cheap complete RTL preflight rejects invalid actions before expensive
            # baseline/netlist work. Success here NEVER qualifies a candidate.
            seen={}
            for vi,repeat,cc,secret,case_count,band in plan:
                if vi not in seen:
                    sd,sm,hit=self._synth(cc,src);cache_hits+=hit;seen[vi]=(sd,sm)
                path=Path(artifacts)/f'preflight-{vi}-{repeat}' if artifacts else None
                self._simulate(cc,src,None,secret,case_count,path,rtl_only=True)
            paired={}
            for vi,repeat,cc,secret,count,band in plan:
                if vi not in paired:
                    sd,sm=seen[vi]
                    baseline=design(cc);bd,bm,hit=self._synth(cc,baseline);cache_hits+=hit
                    paired[vi]=(sd,sm,baseline,bd,bm)
                sd,sm,baseline,bd,bm=paired[vi]
                path=Path(artifacts)/f'case-{vi}-{repeat}' if artifacts else None
                # Private deterministic baseline memoization: exact recipe, toolchain,
                # source/config, workload seed and size. No agent controls this cache.
                bk=digest(self.recipe_fingerprint+self.tool_fingerprint+identity(cc)+baseline+str(secret)+str(count))
                bp=self.root/('baseline-'+bk+'.json')
                if bp.exists():
                    b=json.loads(bp.read_text());baseline_hits+=1
                    if path:
                        (path/'baseline').mkdir(parents=True,exist_ok=True)
                        (path/'baseline'/'private-replay.json').write_text(json.dumps({'config':asdict(cc),'seed':secret,'count':count})+'\n')
                        (path/'baseline'/'candidate.sv').write_text(baseline)
                        (path/'baseline'/'cached-metrics.json').write_text(json.dumps(b)+'\n')
                else:
                    b=self._simulate(cc,baseline,bd,secret,count,path/'baseline' if path else None)
                    bp.write_text(json.dumps(b)+'\n')
                r=self._simulate(cc,src,sd,secret,count,path/'candidate' if path else None)
                if r['cycles']>16*b['cycles']:raise Rejected('throughput floor')
                b.update({k:bm[k] for k in ('cells','logic_depth')});r.update({k:sm[k] for k in ('cells','logic_depth')})
                private.append({'config':asdict(cc),'baseline':b,'candidate':r,'reward':reward(b,r),'target':vi==0})
            targets=[row for row in private if row['target']]
            pub.update({'tested_correct':True,'validation':'rtl_and_netlist_pass','reward':sum(r['reward'] for r in targets)/len(targets),
                        'metrics':{'cells':targets[0]['candidate']['cells'],'logic_depth':targets[0]['candidate']['logic_depth'],
                                   'mean_completion_cycles':sum(r['candidate']['cycles'] for r in targets)/len(targets),
                                   'mean_offered_latency':sum(r['candidate']['offered_latency'] for r in targets)/len(targets)},
                        'paired_ratios':{k:sum(r['candidate'][k]/r['baseline'][k] for r in targets)/len(targets) for k in ('cells','cycles','offered_latency')},
                        'dimension_variants_checked':len(seen),'private_cases_checked':len(private)})
            objectives=scores(private);pub['objectives']=objectives;pub['reward']=objectives[c.objective]['reward'];pub['objective_eligible']=objectives[c.objective]['eligible']
            point={k:sum(ratios(x['baseline'],x['candidate'])[k] for x in targets)/len(targets) for k in ('cells','cycles','latency')}
            pub['pareto_point']=point;pub['baseline_relation']=relation(point)
        except (Rejected,OSError,ValueError,KeyError,TypeError) as e:
            # Do not return vectors, seeds, expected values, tool logs or raw errors.
            msg=str(e);pub['validation']='rejected'
            pub['reason']=next((s for s in ('minimum storage capacity','minimum registered latency','clock contract violation','response deadline','completion deadline','functional mismatch','extra output','stalled response changed','changed interface','logic-depth budget','cell budget','throughput floor','timeout','experimental family') if s in msg),'qualification failed')
            if artifacts:
                Path(artifacts).mkdir(parents=True,exist_ok=True);(Path(artifacts)/'private-error.txt').write_text(msg)
        finally:
            pub['elapsed_s']=round(time.monotonic()-started,3);pub['synthesis_cache_hits']=cache_hits;pub['baseline_simulation_cache_hits']=baseline_hits;pub['recipe_sha256']=self.recipe_fingerprint;pub['tool_fingerprint']=self.tool_fingerprint
            if artifacts:
                Path(artifacts).mkdir(parents=True,exist_ok=True)
                (Path(artifacts)/'result.json').write_text(json.dumps(pub,indent=2)+'\n')
                (Path(artifacts)/'private-results.json').write_text(json.dumps(private,indent=2)+'\n')
        return pub

_default=None
def evaluate(c,source,**kwargs):
    global _default
    if _default is None:_default=TrustedEvaluator()
    return _default.evaluate(c,source,**kwargs)
