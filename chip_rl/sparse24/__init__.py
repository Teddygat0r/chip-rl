"""Experimental compressed 2-of-4 sparse dot+bias+requant family."""
from .spec import Config
from .rtl import design
from .oracle import expected
__all__=['Config','design','expected']
