module candidate #(parameter WIDTH=16, DEPTH=256, K=4)(input clk,input rst,input in_valid,output in_ready,
      input [511:0] in_data,output out_valid,input out_ready,output [255:0] out_data);
    localparam S=1;
    reg [S-1:0] valid; reg [255:0] data[0:S-1]; wire [S:0] ready;
    assign ready[S]=out_ready;
    genvar g;
    generate for(g=0;g<S;g=g+1) begin: elastic_stage
      assign ready[g]=!valid[g] || ready[g+1];
    end endgenerate
    assign in_ready=ready[0] && !rst;
    assign out_valid=valid[S-1] && !rst;
    assign out_data=data[S-1];
    wire fire=in_valid && in_ready;
    reg [255:0] y; integer st;
    reg [31:0] mem[0:(DEPTH-1)]; integer i,cnt,z;
    always @* begin
      y=0;
      cnt=0; if(!in_data[0]) begin for(i=0;i<4;i=i+1) if(in_data[4+i]) begin
          y[8+cnt*32+:32]=mem[in_data[16+i*8+:8]%DEPTH]; cnt=cnt+1; end y[2:0]=cnt; end
    end
    always @(posedge clk) begin
      if(rst) begin
        valid<=0;
        for(st=0;st<S;st=st+1) data[st]<=0;
        for(z=0;z<DEPTH;z=z+1) mem[z]<=0;
      end else begin
        for(st=S-1;st>0;st=st-1) if(ready[st]) begin
          valid[st]<=valid[st-1]; if(valid[st-1]) data[st]<=data[st-1];
        end
        if(ready[0]) begin valid[0]<=in_valid; if(in_valid) data[0]<=y; end
        if(fire) begin if(in_data[0]) mem[in_data[8+:8]%DEPTH]<=in_data[16+:32]; end
      end
    end
    endmodule
    