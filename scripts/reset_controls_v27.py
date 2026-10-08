"""Trusted audit controls, not available as candidate-selected evaluator switches."""
from chip_rl.tasks import Config
from chip_rl.architectures import architecture
from chip_rl.cycle.rtl import design as cycle_design
from chip_rl.memory.rtl import design as memory_design
from chip_rl.memory.spec import Config as MemoryConfig

def config(family):return MemoryConfig('mshr') if family=='mshr' else Config(family)
def source(family,label):
 c=config(family)
 if family=='elastic':s=architecture(c,'fifo4' if label=='alternate' else 'baseline')
 elif family=='mshr':s=memory_design(c,'shift' if label=='alternate' else 'ring')
 else:s=cycle_design(c,alternate='decoded' if label=='alternate' else False)
 if label=='two_edge':
  s=s.replace('always @(posedge clk)begin','always @(posedge clk)begin',1)
  # Only reset state handling is delayed; public handshake reset suppression remains.
  mark='if(rst)'
  assert mark in s;s=s.replace(mark,'if(rst && reset_seen)',1)
  s=s.replace('endmodule','reg reset_seen;always @(posedge clk)reset_seen<=rst;\nendmodule')
 elif label=='retained':
  if family=='elastic':a='valid<=0;';b='if((&valid) && !out_ready && in_data[0]) valid<=valid; else valid<=0;'
  elif family=='mshr':a='state[j]<=0;';b='if(req_valid && count[j]>1) state[j]<=state[j]; else state[j]<=0;'
  else:a='occupied<=0;';b='if(in_valid && (|occupied) && in_data[0]) occupied<=occupied; else occupied<=0;'
  assert a in s;s=s.replace(a,b,1)
 return s
