"""Parameterized candidate programs. Trusted evaluation overrides all dimensions."""
from ._legacy_rtl import design as _design

class Expr:
    def __init__(self,text):self.text=text
    def __str__(self):return self.text
    def __sub__(self,n):return Expr(f'({self.text}-{n})')
    def __rsub__(self,n):return Expr(f'({n}-{self.text})')
    def __floordiv__(self,n):return Expr(f'({self.text}/{n})')
    def __rmul__(self,n):return Expr(f'({n}*{self.text})')

class Parameters:
    def __init__(self,name):
        self.name=name;self.width=Expr('WIDTH');self.depth=Expr('DEPTH');self.k=Expr('K')

def design(c,stages=None,mutant=None):
    # Buffering is the purpose of elastic; other references have one output stage.
    if stages is None:stages=4 if c.name=='elastic' else 1
    source=_design(Parameters(c.name),stages,mutant)
    return source.replace('module candidate(',f'module candidate #(parameter WIDTH={c.width}, DEPTH={c.depth}, K={c.k})(')
