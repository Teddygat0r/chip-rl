`timescale 1ns/1ps
module tb;
reg clk=0; always #5 clk=~clk;
reg rst=1,in_valid=0,out_ready=0;
reg [63:0] in_data=0;
wire in_ready,out_valid;
wire [63:0] out_data;
physical_top dut(.*);
reg [63:0] vectors_in[0:38],vectors_out[0:38];
integer file,rc,i,cycles;
reg [63:0] inword,outword;
initial begin
 file=$fopen("vectors.txt","r");
 if(file==0) $fatal(1,"missing vectors");
 for(i=0;i<39;i=i+1)begin
  rc=$fscanf(file,"%h %h\n",inword,outword);
  if(rc!=2)$fatal(1,"bad vector %0d",i);
  vectors_in[i]=inword;vectors_out[i]=outword;
 end
 $fclose(file);
 repeat(3) @(negedge clk); rst=0;
 for(i=0;i<39;i=i+1)begin
  @(negedge clk); in_data=vectors_in[i];in_valid=1;out_ready=0;
  cycles=0;
  while(!in_ready)begin @(negedge clk);cycles=cycles+1;if(cycles>300)$fatal(1,"input timeout");end
  @(negedge clk);in_valid=0;
  cycles=0;
  while(!out_valid)begin @(negedge clk);cycles=cycles+1;if(cycles>300)$fatal(1,"output timeout case %0d",i);end
  if(out_data!==vectors_out[i])$fatal(1,"mismatch case %0d: got %h expected %h",i,out_data,vectors_out[i]);
  repeat(3)begin @(negedge clk);if(!out_valid || out_data!==vectors_out[i])$fatal(1,"unstable blocked case %0d",i);end
  out_ready=1;@(negedge clk);out_ready=0;
 end
 $display("PASS 39 exact-oracle vectors and blocked-output checks");$finish;
end
endmodule
