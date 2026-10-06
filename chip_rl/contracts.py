"""Trusted, versioned contract limits. Candidate actions cannot modify these."""
import hashlib,json
from dataclasses import asdict
PILOT=('elastic','dot','scratchpad','tensor','cache','gather')
EXPERIMENTAL=('dma','router','scoreboard','accelerator')
LOGIC_LEVEL_LIMIT={'elastic':24,'dot':72,'scratchpad':160,'tensor':80,'cache':96,'gather':160,
                   'dma':128,'router':160,'scoreboard':128,'accelerator':160}
VERSION='mandatory-variable-stream-v3'
def specification(c):
    return {'version':VERSION,'config':asdict(c),'status':'pilot_candidate' if c.name in PILOT else 'experimental_excluded',
            'coverage_profile':'mandatory-variable-stream-v3','random_command_bands':{'target_short':[128,256],'target_long':[1024,1280],'structural':[512,768]},
            'dimensions':{'WIDTH':[8,16,24],'DEPTH':[16,64,256],'K':[2,4]},
            'clock':'single positive-edge clk; synchronous state only; no frequency claim',
            'minimum_response_cycles':1,'maximum_response_cycles':64,
            'elastic_minimum_capacity':4 if c.name=='elastic' else 0,
            'max_completion_cycles_per_command':32,'completion_allowance':128,
            'mapped_logic_depth_limit':LOGIC_LEVEL_LIMIT[c.name],
            'timing_model':'fixed logical cycles and bounded generic gate levels, NOT physical timing closure'}
def identity(c):return hashlib.sha256(json.dumps(specification(c),sort_keys=True).encode()).hexdigest()
