module physical_top(
  input clk,
  input rst,
  input in_valid,
  output in_ready,
  input [63:0] in_data,
  output out_valid,
  input out_ready,
  output [35:0] out_data
);
wire [255:0] full_out;
candidate #(.N(4)) core (.clk(clk),.rst(rst),.in_valid(in_valid),.in_ready(in_ready),.in_data({448'b0,in_data}),.out_valid(out_valid),.out_ready(out_ready),.out_data(full_out));
assign out_data = {full_out[131:128],full_out[31:0]};
endmodule
