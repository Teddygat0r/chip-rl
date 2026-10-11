module physical_top(
  input clk,
  input rst,
  input req_valid,
  output req_ready,
  input [15:0] req_addr,
  input [7:0] req_tag,
  input [7:0] req_aux,
  input inv_valid,
  input [1:0] inv_asid,
  output out_valid,
  input out_ready,
  output [7:0] out_tag,
  output [31:0] out_data,
  output [1:0] out_fault,
  output mem_valid,
  input mem_ready,
  output [15:0] mem_addr,
  output [3:0] mem_tag,
  input resp_valid,
  output resp_ready,
  input [3:0] resp_tag,
  input [127:0] resp_data
);
candidate #(.ENTRIES(2)) core (.clk(clk), .rst(rst), .req_valid(req_valid), .req_ready(req_ready), .req_addr(req_addr), .req_tag(req_tag), .req_aux(req_aux), .inv_valid(inv_valid), .inv_asid(inv_asid), .out_valid(out_valid), .out_ready(out_ready), .out_tag(out_tag), .out_data(out_data), .out_fault(out_fault), .mem_valid(mem_valid), .mem_ready(mem_ready), .mem_addr(mem_addr), .mem_tag(mem_tag), .resp_valid(resp_valid), .resp_ready(resp_ready), .resp_tag(resp_tag), .resp_data(resp_data));
endmodule
