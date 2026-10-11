"""One-stage, mask-decoded gather reference.

The sixteen cases are elaborated into statically placed output words.  This is
an additive experimental source; the frozen baseline and architecture catalog
are deliberately unaffected.
"""

from .tasks import Config


def design(c: Config | None = None) -> str:
    """Return a parameterized ``candidate`` for the gather contract."""
    if c is None:
        c = Config("gather")
    if c.name != "gather":
        raise ValueError("gather configuration required")

    cases = []
    for mask in range(16):
        lanes = [f"lane{i}" for i in range(4) if mask & (1 << i)]
        # A concatenation puts the first selected lane at output bits 8+:32.
        padding = 4 - len(lanes)
        terms = ([f"{padding * 32}'b0"] if padding else []) + lanes[::-1]
        packed_words = terms[0] if len(terms) == 1 else "{" + ", ".join(terms) + "}"
        cases.append(
            f"        4'h{mask:x}: begin packed_words = {packed_words}; count = 3'd{len(lanes)}; end"
        )

    return f'''module candidate #(parameter WIDTH={c.width}, DEPTH={c.depth}, K={c.k})(
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
{chr(10).join(cases)}
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
                    result <= {{120'b0, packed_words, 5'b0, count}};
                end
            end
        end
    end
endmodule'''
