"""Establish whether prior pilot/controller results apply to unchanged runtime code."""
import argparse,subprocess,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--previous-python',required=True);p.add_argument('--current-python',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
code='''import json,hashlib,itertools
from pathlib import Path
import chip_rl
from chip_rl.tasks import Config,NAMES
from chip_rl.contracts import specification
root=Path(chip_rl.__file__).parent
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.py') if 'expansion' not in p.parts and p!=root/'contracts.py'}
contracts=[specification(Config(n,width=w,depth=d,k=k,objective=o)) for n,w,d,k,o in itertools.product(NAMES,(8,12,16,20,24),(16,32,64,128,256),(1,2,3,4),('area','balanced','latency'))]
print(json.dumps({'root':str(root),'files':files,'contract_count':len(contracts),'contracts_sha256':hashlib.sha256(json.dumps(contracts,sort_keys=True).encode()).hexdigest()}))'''
rows=[json.loads(subprocess.run([exe,'-c',code],cwd='/tmp',capture_output=True,text=True,check=True).stdout) for exe in (a.previous_python,a.current_python)]
assert rows[0]['files']==rows[1]['files'];assert rows[0]['contracts_sha256']==rows[1]['contracts_sha256']
a.output.write_text(json.dumps({'previous':rows[0],'current':rows[1],'identical':True,'scope':'All pilot/controller Python files excluding expansion and the root contracts.py; contract outputs compared across 3000 legal parameter/goal combinations. This is identity evidence, not a fresh HDL run.'},indent=2)+'\n')
print('unchanged legacy runtime',len(rows[0]['files']),'files;',rows[0]['contract_count'],'contracts')
