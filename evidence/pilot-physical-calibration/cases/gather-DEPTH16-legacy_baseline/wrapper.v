module physical_top(
  input clk,
  input rst,
  input in_valid,
  output in_ready,
  input [47:0] in_data,
  output out_valid,
  input out_ready,
  output [135:0] out_data
);
wire [255:0] full_out;
candidate #(.DEPTH(16)) core (.clk(clk),.rst(rst),.in_valid(in_valid),.in_ready(in_ready),.in_data({464'b0,in_data}),.out_valid(out_valid),.out_ready(out_ready),.out_data(full_out));
assign out_data = full_out[135:0];
endmodule
