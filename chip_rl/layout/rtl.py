from .spec import HEADER
CATALOG=('row_major','xor','add')
def design(label='row_major'):
 forms={'row_major':'row*COLS+col','xor':'row*COLS+(col ^ (row & (BANKS-1)))','add':'row*COLS+(col/BANKS)*BANKS+((col+row)%BANKS)','rotate_xor':'row*COLS+(col ^ ((((row & (BANKS-1)) << 1) | ((row & (BANKS-1)) >> ($clog2(BANKS)-1))) & (BANKS-1)))'}
 if label not in forms:raise ValueError('layout design')
 return HEADER+'wire [$clog2(ROWS)-1:0] r=row;wire [$clog2(COLS)-1:0] c=col;\nassign addr='+forms[label].replace('row','r').replace('col','c')+';\nendmodule\n'
def mutant(label):
 forms={'alias':'0','out_of_range':'ROWS*COLS','drop_high_col':'row*COLS+(col & (BANKS-1))','unmasked_row':'row*COLS+(col ^ row)','padding':'row*(COLS+1)+col'}
 if label in forms:return HEADER+'assign addr='+forms[label]+';\nendmodule\n'
 if label=='latch':return HEADER.replace('output [9:0]','output reg [9:0]')+'always @* if(row[0])addr=row*COLS+col;endmodule\n'
 if label=='port':return design().replace('[9:0] addr','[8:0] addr')
 if label=='divergence':return design().replace('assign addr=','// synthesis translate_off\nassign addr=')
 raise ValueError('mutant')
