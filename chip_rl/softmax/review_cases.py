"""Review-guided faults. These are visible controls, not independently executed tests."""
from .rtl import design
NEW=('late449','late512','late1024','stall_edge','duplicate','spontaneous')
def attack(label):
 s=design()
 if label.startswith('late'):
  threshold=int(label[4:])-1
  return s.replace('reg [8*N-1:0] command;','reg [10:0] commands; reg [8*N-1:0] command;').replace('if(rst)begin','if(rst)begin commands<=0;').replace('command<=in_data','commands<=commands+1;command<=in_data').replace('<=qtemp[15:0]',f'<=commands>{threshold}?0:qtemp[15:0]')
 if label=='stall_edge':return s.replace('reg [8*N-1:0] command;','reg rst_previous; always @(posedge clk) rst_previous<=rst; reg [8*N-1:0] command;').replace('if(rst)begin','if(rst && (!ov || rst_previous))begin')
 if label=='duplicate':return s.replace('if(ov && out_ready)ov<=0','if(ov && out_ready)ov<=1')
 if label=='spontaneous':return s.replace('if(in_valid && in_ready)begin','if(in_ready)begin')
 raise ValueError('review fault')
