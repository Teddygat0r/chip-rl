"""Reproduce the two product-range SAT checks and exhaustive concrete link check."""
import argparse,json
from pathlib import Path
import chip_rl.quality.components as components
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False);rows=[]
for label,expr in [('signed','a*b'),('unsigned-mutant','$unsigned(a)*$unsigned(b)')]:
 h='module formal_top(input signed [7:0] a,b);wire signed [15:0] p='+expr+';always @* begin assert(p>=-16256);assert(p<=16384);end endmodule'
 original=components.run
 def bounded(cmd,cwd,label,timeout):
  script=Path(cwd)/'formal.ys';script.write_text(script.read_text().replace('-timeout 30','-timeout 20'))
  return original(cmd,cwd,label,35)
 components.run=bounded
 try:r=components.sat(a.output/label,'',h,metadata={'kind':'signed_product_range_linkage','solver_timeout_s':20,'wall_timeout_s':35})
 finally:components.run=original
 rows.append(r);print(label,r['status'],flush=True)
rows.append(components.exhaustive_product(a.output/'exhaustive'))
(a.output/'results.json').write_text(json.dumps(rows,indent=2))
