"""Valid competing expressions and source-only negative controls for layout qualification."""
from .rtl import design,mutant
from .spec import HEADER

def correct(label):
 if label in ('row_major','xor','add'):return design(label)
 if label=='wildcard':return design('row_major').replace('output [9:0]','output reg [9:0]').replace('assign addr=','always @(*) addr=')
 if label=='always_comb':return design('xor').replace('output [9:0]','output reg [9:0]').replace('assign addr=','always_comb addr=')
 if label=='function':return HEADER+'''function automatic [9:0] place;
 input [$clog2(ROWS)-1:0] r;input [$clog2(COLS)-1:0] c;
 begin place=r*COLS+(c/BANKS)*BANKS+((c+r)%BANKS);end endfunction
 assign addr=place(row[$clog2(ROWS)-1:0],col[$clog2(COLS)-1:0]);endmodule
'''
 if label=='column_major':return design().replace('r*COLS+c','c*ROWS+r')
 raise ValueError('correct implementation')

def bad(label):
 if label in ('alias','out_of_range','drop_high_col','unmasked_row','padding','latch','port','divergence'):return mutant(label)
 if label=='manual_sensitivity':return correct('wildcard').replace('@(*)','@(row or col[0])')
 if label=='extra_read_port':return design().replace('output [9:0] addr','output [9:0] addr,output [9:0] addr2').replace('endmodule','assign addr2=addr;endmodule')
 if label=='hidden_state':return HEADER+'''reg [5:0] last_row;always @(posedge col[0])last_row<=row;assign addr=last_row*COLS+col;endmodule'''
 if label=='uncounted_rom':return HEADER+'''reg [9:0] table_mem[0:1023];initial $readmemh("private.hex",table_mem);assign addr=table_mem[row*COLS+col];endmodule'''
 if label=='attribute':return design().replace('assign addr=','(* keep = 1 *) assign addr=')
 raise ValueError('negative control')
