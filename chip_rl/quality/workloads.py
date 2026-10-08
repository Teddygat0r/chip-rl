import random
from .oracles import PageTables,arithmetic,independent
from ..memory.workloads import generate as old_generate

def generate(c,seed,heldout=False,mode='stream'):
 if c.name=='tlb':
  w=old_generate(c,seed,heldout);pages=PageTables(seed^0x789);w['page_tables']=pages.tables
  for e in w['epochs']:
   for req in e['requests']:
    y,f=pages.translate(req['addr'],req['aux'],e['generation']);assert (y,f)==pages.flat_translate(req['addr'],req['aux'],e['generation'])
    req.update(data=y,fault=f)
  # Directed, unscored reuse of a root pointer across an ASID invalidation.
  # Select a concrete moved pointer whose stale read produces a different answer.
  # Coverage failure is an error, never a silent pass on an unsuitable seed.
  extra=[];probes=[]
  for asid in range(4):
   for generation in range(3):
    probe=None
    for vpn in range(256):
     addr=(vpn<<8)|0x5a;rootaddr=0x8000+asid*256+(vpn>>4)*4
     before=pages.tables[generation][rootaddr];after=pages.tables[generation+1][rootaddr]
     want=pages.translate(addr,asid,generation+1)
     if not before&1 or not after&1 or (before&0xfffc)==(after&0xfffc) or want[1]:continue
     stale=pages.tables[generation+1][(before&0xfffc)+(vpn&15)*4]
     got=(0,1) if not stale&1 else (0,2) if not stale&2 else (((stale>>8)&255)*256+0x5a,0)
     if got!=want:probe=addr;break
    if probe is None:raise ValueError('root invalidation coverage precondition unavailable')
    # Warm the target alone (works with a one-entry root cache), then change only that ASID and verify both contexts. All probes are unscored.
    other=(asid+1)%4
    for phase in (0,1):
     requests=[]
     for context in ((asid,) if phase==0 else (asid,other)):
      gen=generation+phase if context==asid else generation
      data,fault=pages.translate(probe,context,gen);assert (data,fault)==pages.flat_translate(probe,context,gen)
      requests.append({'addr':probe,'aux':context,'data':data,'fault':fault})
     extra.append({'requests':requests,'generation':generation+phase,'reset':phase==0,'invalidate':phase==1,'interrupt':0,'inflight':0,'probe':3,'target_asid':asid if phase else -1})
    probes.append({'address':probe,'asid':asid,'from_generation':generation,'to_generation':generation+1})
  w['epochs']=extra+w['epochs'];w['root_invalidation_probes']=probes
  return w
 r=random.Random(seed);xs=[];n=128 if heldout else 96
 for i in range(n):
  x=r.getrandbits(1024)
  for row in range(c.m):
   for k in range(c.k):
    v=((-128,-128,127,0,1,-1)[i] if i<6 else r.randrange(-128,128))&255;off=8*(16*row+k);x=(x&~(255<<off))|(v<<off)
  for k in range(c.k):
   for col in range(c.n):
    v=((-128,127,127,-128,-1,1)[i] if i<6 else r.randrange(-128,128))&255;off=512+8*(4*k+col);x=(x&~(255<<off))|(v<<off)
  assert arithmetic(c,x)==independent(c,x);xs.append(x)
 period=1 if mode=='stream' else 8
 return {'inputs':xs,'expected':[arithmetic(c,x) for x in xs],'release':[0 if i<4 else (i-3)*period for i in range(n)],'ready':[int(r.randrange(8)!=0) for _ in range(c.max_cycles)],'seed':seed,'mode':mode}
