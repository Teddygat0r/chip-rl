"""Same-author adversarial controls, deliberately outside the candidate action interface."""
from .rtl import design,bad
OLD=('uniform','ignore_mask','unsigned','narrow_sum','coarse','stalled_expiry','live_input','wrong_scale','stuck','reverse','absolute','reset_during_division')
NEW=('mask_delta17','single_edge_reset','drop_tail','drop_output','narrow_signed','constant_zero','winner_only','late_zero','max_mask','absolute_shift')
def attack(label):
 if label in OLD:return bad(label)
 s=design('full_serial')
 changes={
 'mask_delta17':("active[index]?exponential(delta[7:0]):17'b0","active[index] && !(active==3 && delta==17)?exponential(delta[7:0]):17'b0"),
 'drop_tail':("active[index]?exponential(delta[7:0]):17'b0","active[index] && delta<80?exponential(delta[7:0]):17'b0"),
 'drop_output':('<=qtemp[15:0]','<=qtemp<16?0:qtemp[15:0]'),
 'narrow_signed':('wire signed [8:0] value','wire signed [6:0] value'),
 'constant_zero':('<=qtemp[15:0]','<=0'),
 'winner_only':("active[index]?exponential(delta[7:0]):17'b0","active[index] && delta==0?exponential(delta[7:0]):17'b0"),
 'max_mask':('active[index] && value>maximum','value>maximum'),
 'absolute_shift':('delta=maximum-value',"delta=maximum-value+((maximum==9'sd127 && value!=maximum)?9'd2:9'd0)")}
 if label=='single_edge_reset':return s.replace('reg [8*N-1:0] command;','reg rst_previous; always @(posedge clk) rst_previous<=rst; reg [8*N-1:0] command;').replace('if(rst)begin','if(rst && rst_previous)begin')
 if label=='late_zero':return s.replace('reg [8*N-1:0] command;','reg [9:0] commands; reg [8*N-1:0] command;').replace('if(rst)begin','if(rst)begin commands<=0;').replace('command<=in_data','commands<=commands+1;command<=in_data').replace('<=qtemp[15:0]','<=commands>256?0:qtemp[15:0]')
 old,new=changes[label];assert old in s;return s.replace(old,new)
