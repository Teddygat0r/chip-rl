"""Reviewed pilot alternatives. Experimental v1 alternatives are archived."""
from .architectures import architecture,CATALOG
STRATEGIES={n:labels[-1] for n,labels in CATALOG.items()}
def alternate(c,stages=None):
    if stages is not None:raise ValueError('choose an architecture, not output padding')
    return architecture(c,STRATEGIES[c.name])
