"""Optional ORFS launcher. Never invent physical metrics or treat setup as verification.
Usage: python -m chip_rl.physical TASK --flow-root /path/OpenROAD-flow-scripts/flow --output DIR
The flow/PDK is trusted infrastructure supplied by the host, not a candidate action.
"""
import argparse,json,shutil
from pathlib import Path
from .tasks import Config,NAMES
from .rtl import design
from .evaluate import evaluate,run,Rejected

def physical(c,source,flow_root,output):
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False)
    result={'status':'not_run','physical_verified':False,'metrics':None}
    flow=Path(flow_root).resolve()
    if not (flow/'Makefile').is_file() or not (flow/'platforms/nangate45').is_dir():
        result['error']='ORFS flow Makefile and Nangate45 platform required'
    elif any(ch in str(out) for ch in ' \n\r\t$#;'):
        result['error']='use an output path without whitespace or make metacharacters'
    else:
        qual=evaluate(c,source,artifacts=out/'qualification')
        if not qual['tested_correct']:result['error']='functional/synthesis qualification failed'
        else:
            (out/'candidate.sv').write_text(source)
            (out/'constraint.sdc').write_text('create_clock -name clk -period 10.0 [get_ports clk]\nset_input_delay 1.0 -clock clk [remove_from_collection [all_inputs] [get_ports clk]]\nset_output_delay 1.0 -clock clk [all_outputs]\n')
            (out/'config.mk').write_text(f'''export DESIGN_NAME = candidate
export PLATFORM = nangate45
export VERILOG_FILES = {out}/candidate.sv
export SDC_FILE = {out}/constraint.sdc
export CORE_UTILIZATION = 30
export TNS_END_PERCENT = 100
export RESULTS_DIR = {out}/results
export REPORTS_DIR = {out}/reports
export LOG_DIR = {out}/logs
export OBJECTS_DIR = {out}/objects
''')
            try:
                run(['make','-C',str(flow),'DESIGN_CONFIG='+str(out/'config.mk'),'finish'],out,'openroad-flow',1200)
                final=list((out/'results').rglob('6_final.odb'))
                reports=list((out/'reports').rglob('*'))
                if not final or not any(p.is_file() for p in reports):raise Rejected('no final database/reports; incomplete physical flow')
                # Preserve raw flow output for explicit review; schema changes must not fabricate metrics.
                result['status']='completed_requires_report_review'
                result['reports']=[str(p.relative_to(out)) for p in reports if p.is_file()]
                result['note']='Review timing, DRC, placement/routing and library assumptions before claiming physical validity; not included in reward.'
            except (Rejected,OSError) as e:result['error']=str(e);result['status']='failed'
    (out/'physical-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task',choices=NAMES);p.add_argument('--rtl',type=Path);p.add_argument('--flow-root',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    c=Config(a.task);r=physical(c,a.rtl.read_text() if a.rtl else design(c),a.flow_root,a.output)
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='completed_requires_report_review' else 1)
