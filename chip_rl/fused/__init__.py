"""Experimental exact fused dot+bias+requant evaluation."""
from .spec import Config
from .rtl import design
from .oracle import expected
__all__=['Config','design','expected']
