"""Carry forward unchanged HDL evidence after a monotone source rejection gate."""
import argparse,ast,json,subprocess,zipfile
from pathlib import Path
from chip_rl.layout.spec import Config,HEADER
from chip_rl.layout.synthesis import source_gate
from chip_rl.layout.evaluate import Evaluator
from chip_rl.layout.rtl import design
p=argparse.ArgumentParser();p.add_argument('--matrix',type=Path,required=True);p.add_argument('--prior-wheel',type=Path,required=True);p.add_argument('--final-wheel',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--cache',required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
old=zipfile.ZipFile(a.prior_wheel);new=zipfile.ZipFile(a.final_wheel);runtime=[n for n in old.namelist() if n.startswith('chip_rl/')];changed=[n for n in runtime if old.read(n)!=new.read(n)];assert changed==['chip_rl/layout/synthesis.py'],changed
oldtree=ast.parse(old.read(changed[0]));newtree=ast.parse(new.read(changed[0]));klass=lambda t:next(x for x in t.body if isinstance(x,ast.ClassDef) and x.name=='Synthesis');compilefn=lambda t:next(x for x in klass(t).body if isinstance(x,ast.FunctionDef) and x.name=='compile')
x,y=compilefn(oldtree),compilefn(newtree)
assert ast.dump(ast.Module(body=x.body[4:],type_ignores=[]))==ast.dump(ast.Module(body=y.body[1:],type_ignores=[]))
assert isinstance(y.body[0],ast.Expr) and y.body[0].value.func.id=='source_gate'
# Explicitly compare the gate-free inspector and synthesis constructor too.
for name in ('inspect',):
 f=lambda t:next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==name)
 assert ast.dump(f(oldtree))==ast.dump(f(newtree))
accepted=[]
for row in json.loads((a.matrix/'results.json').read_text()):
 if row['expected_correct']:
  source_gate((a.matrix/row['case']/'candidate.sv').read_text());accepted.append(row['case'])
q=Evaluator(a.cache);before=json.loads((a.matrix/'development-row_major/result.json').read_text());journal=json.loads((a.matrix/'development-row_major/private-run.json').read_text())
r=q.evaluate(Config(),design(),replay_seed=journal['seed'],artifacts=a.output/'baseline')
for key in ('tested_correct','reward','cases','tool_fingerprint'):assert r[key]==before[key],key
bad=HEADER.replace('output [9:0]','output reg [9:0]')+'always @(row or col[0]) addr=row*COLS+col;endmodule\n';b=q.evaluate(Config(),bad,replay_seed=190190,artifacts=a.output/'manual-sensitivity');assert not b['tested_correct'] and b['reward']==0
assert not list((a.output/'manual-sensitivity/tool-logs').glob('*'))
result={'only_runtime_change':'additive source gate in layout/synthesis.py; synthesis cache recipe changes as expected','unchanged_synthesis_body_and_inspector':True,'unchanged_all_other_runtime_files':len(runtime)-1,'prior_valid_sources_pass_final_gate':accepted,'baseline_metrics_exact':True,'manual_sensitivity_rejected_before_tools':True,'initial_recipe_sha256':before['recipe_sha256'],'final_recipe_sha256':r['recipe_sha256'],'full_matrix_rerun':False,'reason':'bounded simulation budget; unchanged HDL generation, engine, oracle, synthesis commands and scoring are byte/AST checked'}
(a.output/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
