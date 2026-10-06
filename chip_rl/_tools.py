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

