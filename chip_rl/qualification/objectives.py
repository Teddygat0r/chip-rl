"""Explicit cycle-level integration scenarios, not physical timing claims."""
import math
PROFILES={
 'coalesce':{'name':'half_rate_request_front_end','minimum_commands_per_clock':0.45,'maximum_offered_latency':64,'offered_period':2},
 'histogram':{'name':'one_in_three_counter_updates','minimum_commands_per_clock':0.30,'maximum_offered_latency':64,'offered_period':3},
 'ecc':{'name':'saturated_integrity_stream','minimum_commands_per_clock':0.50,'maximum_offered_latency':None,'offered_period':1},
}
def assess(candidate,baseline):
 name=candidate['config']['name'];p=PROFILES[name].copy();r={'scenario':p,'eligible':False,'reward':0.,'physical_timing_claim':False}
 if not candidate['tested_correct'] or not baseline['tested_correct']:return r
 if candidate['epochs_sha256']!=baseline['epochs_sha256']:raise ValueError('unpaired deep workloads')
 throughput=candidate['responses']/candidate['active_cycles'];latency=candidate['maximum_offered_latency']
 ok=throughput>=p['minimum_commands_per_clock'] and (p['maximum_offered_latency'] is None or latency<=p['maximum_offered_latency'])
 ratio=candidate['synthesis']['cells']/baseline['synthesis']['cells']
 r.update(eligible=ok,commands_per_clock=throughput,maximum_offered_latency=latency,area_ratio=ratio,reward=(1-.5*math.tanh(math.log(ratio))) if ok else 0.)
 return r
