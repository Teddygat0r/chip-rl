from .rtl import design
COMMON=('zero','wrong_clock','drop','no_reset','stall','unstable','unknown_result','unknown_request')
CATALOG={'mshr':COMMON+('wrong_word','tag_alias','lose_waiter','duplicate_fetch','early_free','capacity1','late_drop'),
         'tlb':COMMON+('ignore_asid','ignore_permission','ignore_valid','ignore_invalidate','stale_walk','wrong_pointer','wrong_offset','capacity1','late_drop')}
def bad(c,name):
 s=design(c)
 if name=='zero':s=s.replace('assign out_data=od;','assign out_data=0;')
 elif name=='wrong_clock':s=s.replace('@(posedge clk)','@(negedge clk)')
 elif name=='drop':s=s.replace('ov<=1;','ov<=0;')
 elif name=='no_reset':s=s.replace('if(rst)begin','if(1\'b0)begin')
 elif name=='stall':s=s.replace('assign req_ready=!rst','assign req_ready=1\'b0 && !rst')
 elif name=='unstable':s=s.replace('assign out_data=od;','assign out_data=od^req_addr;')
 elif name=='unknown_result':s=s.replace('assign out_tag=ot;',"assign out_tag=8'bx;").replace('assign out_data=od;',"assign out_data=32'bx;").replace('assign out_fault=0;',"assign out_fault=2'bx;").replace('assign out_fault=ofault;',"assign out_fault=2'bx;")
 elif name=='unknown_request':s=s.replace('assign mem_addr=ma;',"assign mem_addr=16'bx;")
 elif name=='wrong_word':s=s.replace('>>(words[pick_out*4+head[pick_out]]*32)','>>0')
 elif name=='tag_alias':s=s.replace('ot<=tags[pick_out*4+head[pick_out]]','ot<=0')
 elif name=='lose_waiter':s=s.replace('count[target]<=count[target]+1','count[target]<=count[target]')
 elif name=='duplicate_fetch':s=s.replace('if(state[i]!=0 && line[i]==req_addr[15:2])match_idx=i;','if(1\'b0)match_idx=i;')
 elif name=='early_free':s=s.replace('if(count[oi]==1)','if(1\'b1)')
 elif name=='ignore_asid':s=s.replace(' && asid[i]==req_aux[1:0]','')
 elif name=='ignore_permission':s=s.replace('permitted=a[3]?f[3]:(a[2]?f[2]:f[1]);','permitted=1;')
 elif name=='ignore_valid':s=s.replace('if(!resp_data[0])','if(1\'b0)').replace('!resp_data[0]?1:',"1'b0 ? 1:").replace('resp_data[0] && permitted','permitted')
 elif name=='ignore_invalidate':s=s.replace('if(inv_valid)begin','if(1\'b0)begin').replace('(inv_valid && aux[resp_tag][1:0]==inv_asid)',"1'b0")
 elif name=='stale_walk':
  start=s.index(' for(j=0;j<WALKERS;j=j+1)if(state[j]!=0')
  end=s.index('\n end\n end end endmodule',start)
  s=s[:start]+s[end:];s=s.replace('dirty[resp_tag] || (inv_valid && aux[resp_tag][1:0]==inv_asid)',"1'b0")
 elif name=='wrong_pointer':s=s.replace("{resp_data[15:2],2'b00}","16'h1000")
 elif name=='wrong_offset':s=s.replace('va[resp_tag][7:0]',"8'b0").replace('req_addr[7:0]',"8'b0")
 elif name=='capacity1':
  s=s.replace('localparam ACTIVE=ENTRIES;', 'localparam ACTIVE=1;') if c.name=='mshr' else s.replace('victim<=victim==ENTRIES-1?0:victim+1;', 'victim<=0;')
 elif name=='late_drop':
  s=s.replace('localparam ', 'reg [7:0] completions;always @(posedge clk)if(rst)completions<=0;else if(ov && out_ready)completions<=completions+1;\nlocalparam ',1)
  s=s.replace('assign out_valid=!rst && ov;','assign out_valid=!rst && ov && completions<96;')
 else:raise ValueError('fault')
 assert s!=design(c),name
 return s
