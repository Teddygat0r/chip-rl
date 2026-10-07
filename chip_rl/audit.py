"""Trusted, durable evaluation journals. Never returned to candidate actions."""
from contextvars import ContextVar
from dataclasses import asdict,is_dataclass
from functools import wraps
from pathlib import Path
import hashlib,json,os,platform,secrets,sys,tempfile,traceback
ACTIVE=ContextVar('chip_rl_private_trace',default=None)

def write(path,value):
 p=Path(path);tmp=p.with_suffix(p.suffix+'.tmp')
 with tmp.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)

def root():
 p=Path(os.environ.get('CHIP_RL_TRACE_ROOT',str(Path(tempfile.gettempdir())/f'chip-rl-private-{os.getuid()}')))
 p.mkdir(parents=True,exist_ok=True);p.chmod(0o700)
 return p

def journal(fn):
 @wraps(fn)
 def wrapped(self,*args,**kwargs):
  directory=Path(kwargs['artifacts']) if kwargs.get('artifacts') else Path(tempfile.mkdtemp(prefix='eval-',dir=root()))
  directory.mkdir(parents=True,exist_ok=True);directory.chmod(0o700)
  seed=kwargs.get('replay_seed');seed=secrets.randbits(128) if seed is None else seed
  kwargs=dict(kwargs,artifacts=directory,replay_seed=seed)
  config=asdict(args[0]) if args and is_dataclass(args[0]) else repr(args[:1])
  record={'status':'started','evaluator':fn.__module__+'.'+fn.__qualname__,'seed':seed,'config':config,'python':sys.version,'platform':platform.platform(),'pid':os.getpid(),'logs':[]}
  if len(args)>1 and is_dataclass(args[1]):record['action']=asdict(args[1])
  if len(args)>1 and isinstance(args[1],str):
   (directory/'candidate.sv').write_text(args[1]);record['source_sha256']=hashlib.sha256(args[1].encode()).hexdigest()
  write(directory/'private-run.json',record)
  token=ACTIVE.set(directory)
  try:
   result=fn(self,*args,**kwargs);record['status']='completed';record['tested_correct']=result.get('tested_correct');return result
  except BaseException as e:
   record['status']='raised';record['error_type']=type(e).__name__
   (directory/'private-exception.txt').write_text(traceback.format_exc());raise
  finally:
   # A SIGKILL can leave status=started; seed/source and streamed tool logs survive.
   record['logs']=sorted(x.name for x in (directory/'tool-logs').glob('*.log'))
   write(directory/'private-run.json',record);ACTIVE.reset(token)
 return wrapped

def tool_log(label):
 p=ACTIVE.get()
 if p is None:return None
 d=p/'tool-logs';d.mkdir(exist_ok=True)
 fd,name=tempfile.mkstemp(prefix=label+'-',suffix='.log',dir=d);os.close(fd)
 return Path(name)
