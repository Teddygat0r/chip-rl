"""Trusted test-only artifact capture; does not change requests or evaluation."""
import os
from pathlib import Path
root=os.environ.get('CHIP_RL_CAPTURE_ROOT')
if root:
 from chip_rl.expansion.evaluate import Evaluator
 original=Evaluator.evaluate
 count=0
 def captured(self,c,src,**kwargs):
  global count
  count+=1
  if kwargs.get('artifacts') is None:kwargs['artifacts']=Path(root)/f'{os.getpid()}-{count}-{c.name}'
  return original(self,c,src,**kwargs)
 Evaluator.evaluate=captured
