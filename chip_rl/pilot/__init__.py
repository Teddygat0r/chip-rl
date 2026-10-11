"""Single-configuration parameter-holdout pilot.

Public results report finite source/mapped correctness and raw generic-cell proxies;
no common normalized reward or unseen-task claim is made.
"""
from .manifest import SPLITS, PARAMETERS, frozen_manifest, validate_request
from .runner import run_case

__all__ = ['SPLITS', 'PARAMETERS', 'frozen_manifest', 'validate_request', 'run_case']
