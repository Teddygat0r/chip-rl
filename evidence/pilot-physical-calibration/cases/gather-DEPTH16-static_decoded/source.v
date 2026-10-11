module candidate #(parameter WIDTH=16, DEPTH=256, K=4)(
    input clk, input rst, input in_valid, output in_ready,
    input [511:0] in_data, output out_valid, input out_ready,
    output [255:0] out_data
);
    reg [31:0] mem[0:DEPTH-1];
    reg valid;
    reg [255:0] result;
    wire [31:0] lane0 = mem[in_data[16+:8] % DEPTH];
    wire [31:0] lane1 = mem[in_data[24+:8] % DEPTH];
    wire [31:0] lane2 = mem[in_data[32+:8] % DEPTH];
    wire [31:0] lane3 = mem[in_data[40+:8] % DEPTH];
    reg [127:0] packed_words;
    reg [2:0] count;
    integer z;

    assign in_ready = !rst && (!valid || out_ready);
    assign out_valid = !rst && valid;
    assign out_data = result;

    always @* begin
        packed_words = 0;
        count = 0;
        case (in_data[7:4])
        4'h0: begin packed_words = 128'b0; count = 3'd0; end
        4'h1: begin packed_words = {96'b0, lane0}; count = 3'd1; end
        4'h2: begin packed_words = {96'b0, lane1}; count = 3'd1; end
        4'h3: begin packed_words = {64'b0, lane1, lane0}; count = 3'd2; end
        4'h4: begin packed_words = {96'b0, lane2}; count = 3'd1; end
        4'h5: begin packed_words = {64'b0, lane2, lane0}; count = 3'd2; end
        4'h6: begin packed_words = {64'b0, lane2, lane1}; count = 3'd2; end
        4'h7: begin packed_words = {32'b0, lane2, lane1, lane0}; count = 3'd3; end
        4'h8: begin packed_words = {96'b0, lane3}; count = 3'd1; end
        4'h9: begin packed_words = {64'b0, lane3, lane0}; count = 3'd2; end
        4'ha: begin packed_words = {64'b0, lane3, lane1}; count = 3'd2; end
        4'hb: begin packed_words = {32'b0, lane3, lane1, lane0}; count = 3'd3; end
        4'hc: begin packed_words = {64'b0, lane3, lane2}; count = 3'd2; end
        4'hd: begin packed_words = {32'b0, lane3, lane2, lane0}; count = 3'd3; end
        4'he: begin packed_words = {32'b0, lane3, lane2, lane1}; count = 3'd3; end
        4'hf: begin packed_words = {lane3, lane2, lane1, lane0}; count = 3'd4; end
        endcase
    end

    always @(posedge clk) begin
        if (rst) begin
            valid <= 0;
            result <= 0;
            for (z = 0; z < DEPTH; z = z + 1) mem[z] <= 0;
        end else if (!valid || out_ready) begin
            valid <= in_valid;
            if (in_valid) begin
                if (in_data[0]) begin
                    mem[in_data[8+:8] % DEPTH] <= in_data[16+:32];
                    result <= 0;
                end else begin
                    result <= {120'b0, packed_words, 5'b0, count};
                end
            end
        end
    end
endmodule