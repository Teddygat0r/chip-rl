import random
from .oracles import Memory,PageTables

def generate(c,seed,heldout=False):
 r=random.Random(seed);epochs=[];memory=Memory(seed^0xabc);pages=PageTables(seed^0x789)
 for phase in range(4):
  requests=[]
  for i in range(192 if heldout else 128):
   if c.name=='mshr':
    # Four requests to one line, interspersed with independent misses and all words.
    line=(i//4)%16 if i<64 else r.randrange(16384)
    if i>=64 and i%8<4:line=(i//8+17)%16384
    addr=line*4+(i%4);aux=0;y,fault=memory.load(addr),0
   else:
    vpn=(i//4)%16 if i<64 else r.randrange(256);addr=(vpn<<8)|r.randrange(256);aux=r.randrange(16)
    if i<8:
     vpn,aux=((0,0),(0,1),(0,4),(1,0),(2,8),(0,8),(0,0),(0,1))[i];addr=(vpn<<8)|r.randrange(256)
    y,fault=pages.translate(addr,aux,phase)
   requests.append({'addr':addr,'aux':aux,'data':y,'fault':fault})
  epochs.append({'requests':requests,'generation':phase,'reset':phase in (0,2),'invalidate':phase in (1,3),'interrupt':0,'inflight':1+phase%3 if c.name=='tlb' else 0})
 # Interrupted runs reset/cancel both CPU and memory. No stale work may reappear.
 cut={'requests':epochs[0]['requests'][:32],'generation':0,'reset':True,'invalidate':False,'interrupt':1 if c.name=='tlb' else c.entries,'inflight':0}
 epochs.insert(1,cut);epochs.insert(2,dict(epochs[0],reset=True,inflight=2 if c.name=='tlb' else 0))
 for e in epochs:e['probe']=0
 if c.name=='tlb':
  probes=[]
  for vpn in range(16,16+c.entries):
   addr=(vpn<<8)|r.randrange(256);y,fault=pages.translate(addr,0,0);probes.append({'addr':addr,'aux':0,'data':y,'fault':fault})
  for probe in (2,1):epochs.insert(0,{'requests':probes,'generation':0,'reset':probe==1,'invalidate':False,'interrupt':0,'inflight':0,'probe':probe})
 controls=[r.getrandbits(8) for _ in range(c.max_cycles+256)]
 for i in range(64):controls[i]=(controls[i]|5)&~2
 return {'epochs':epochs,'controls':controls,'lines':memory.lines,'page_tables':pages.tables,'seed':seed,'heldout':heldout}
