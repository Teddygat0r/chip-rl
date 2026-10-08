"""Unscored directed persistence/masked-word/reset checks, independent of workload mix."""
import random

def probes(s,seed):
 rng=random.Random(seed ^ 0x202020);qs=[]
 def emit(ids,mask,write,kind,values=None,reset=False):
  qs.append({'coords':[divmod(i%s.words,s.cols) for i in ids],'mask':mask,'write':write,'values':values if values is not None else [rng.getrandbits(32) for _ in ids],'kind':kind,'reset_before':reset,'stall':3,'epoch':0})
 full=(1<<s.lanes)-1
 for start in range(0,s.words,s.lanes):
  ids=list(range(start,start+s.lanes));emit(ids,full,True,'probe-fill',[((i+1)*0x9e3779b1)&0xffffffff for i in ids],reset=start==0)
 for start in range(0,s.words,s.lanes):
  ids=list(range(start,start+s.lanes));emit(ids,sum(1<<i for i in range(0,s.lanes,2)),True,'probe-partial-write');emit(ids,full,False,'probe-partial-preserve')
 for address in (0,s.words-1):
  emit([address]*s.lanes,full^(1<<(s.lanes-1)),True,'probe-duplicate-write',list(range(100,100+s.lanes)))
  emit([address]*s.lanes,full,False,'probe-last-active-writer')
 emit(list(range(s.lanes)),0,True,'probe-empty-store',[0xffffffff]*s.lanes)
 # Different ordering revisits older words after all intervening overwrites.
 for start in reversed(range(0,s.words,s.lanes)):emit(list(range(start,start+s.lanes)),full,False,'probe-persistence')
 # Unlike the scored initialization, these reads occur before any post-reset fill.
 for start in range(0,s.words,s.lanes):emit(list(range(start,start+s.lanes)),full,False,'probe-reset-zero',reset=start==0)
 emit(list(range(s.lanes)),1,True,'probe-post-reset-partial',[0xa5000000+i for i in range(s.lanes)])
 for start in range(0,s.words,s.lanes):emit(list(range(start,start+s.lanes)),full,False,'probe-post-reset-preserve')
 return qs
