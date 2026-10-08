import unittest,random,io,json
from unittest.mock import patch
from chip_rl.quality.spec import Config,configurations,specification,validate_profile
from chip_rl.quality.oracles import PageTables,arithmetic,independent
from chip_rl.quality.workloads import generate
from chip_rl.quality.rtl import CATALOG,design
from chip_rl.quality.mutants import CATALOG as BAD,bad
from chip_rl.quality.server import serve
class Quality(unittest.TestCase):
 def test_independent_arithmetic(self):
  rng=random.Random(3)
  for m,n,k in ((1,1,1),(2,2,8),(4,4,16)):
   c=Config('tensor',m=m,n=n,k=k)
   for _ in range(20):
    x=rng.getrandbits(1024);self.assertEqual(arithmetic(c,x),independent(c,x))
 def test_extreme_and_padding(self):
  c=Config('dot',k=16);x=int.from_bytes(bytes([128])*128,'little')
  self.assertEqual(arithmetic(c,x),16*16384)
  self.assertEqual(arithmetic(c,x),arithmetic(c,x^(255<<1016)))
 def test_page_oracles_and_full_capacity(self):
  p=PageTables(7)
  for g in range(4):
   for vpn in range(256):
    for aux in range(16):self.assertEqual(p.translate(vpn*256+7,aux,g),p.flat_translate(vpn*256+7,aux,g))
   for vpn in range(16,32):self.assertEqual(p.translate(vpn*256,0,g)[1],0)
 def test_strict_bounds(self):
  for kw in ({'k':True},{'k':17},{'entries':17},{'m':0},{'max_cycles':20001},{'max_cells':250001}):
   with self.assertRaises(ValueError):Config('tensor',**kw)
  with self.assertRaises(ValueError):Config('dot',m=2)
 def test_structural_split(self):
  for name in CATALOG:
   dev=set(configurations(Config(name)));hold=set(configurations(Config(name),True));self.assertFalse(dev&hold)
 def test_reproducible_workload(self):
  c=Config('dot');a=generate(c,1);self.assertEqual(a,generate(c,1));self.assertNotEqual(a,generate(c,2));self.assertNotEqual(a['release'],generate(c,1,mode='compact')['release'])
 def test_protocol_available(self):self.assertIn('512+8',specification(Config('tensor'))['protocol'])
 def test_catalog_and_mutants(self):
  for n in CATALOG:
   c=Config(n);self.assertEqual(len(set(design(c,l) for l in CATALOG[n])),len(CATALOG[n]))
   for b in BAD[n]:self.assertNotEqual(bad(c,b),design(c))
 def test_source_only_boundary(self):
  inp=io.StringIO('\n'.join(json.dumps(x) for x in [{'op':'reset','task':'dot','artifacts':'/tmp/x'},{'op':'reset','task':'dot','replay_seed':7},{'op':'reset','task':'dot','k':1}])+'\n');out=io.StringIO();serve(inp,out)
  self.assertTrue(all(not json.loads(s)['ok'] for s in out.getvalue().splitlines()))

 def test_ignored_host_dimensions_rejected(self):
  for c in (Config('dot',k=16),Config('tensor',m=2),Config('tlb',entries=8)):
   with self.assertRaises(ValueError):validate_profile(c)
  validate_profile(Config('dot'))
 def test_environment_rejects_override_before_tools(self):
  from chip_rl.quality.env import QualityEnv
  with patch('chip_rl.quality.env.Evaluator',side_effect=AssertionError('tools must not run')):
   with self.assertRaises(ValueError):QualityEnv('tlb',entries=8)
 def test_directed_root_invalidation_probe(self):
  for seed in range(20):
   c=Config('tlb');w=generate(c,seed);a,b=w['epochs'][:2]
   self.assertEqual((a['probe'],b['probe']),(3,3));self.assertTrue(a['reset']);self.assertTrue(b['invalidate']);self.assertEqual(a['requests'][0]['addr'],b['requests'][0]['addr'])
   pages=PageTables(seed^0x789);req=b['requests'][0];asid=req['aux'];vpn=req['addr']>>8;root=0x8000+asid*256+(vpn>>4)*4
   self.assertNotEqual(pages.tables[0][root]&0xfffc,pages.tables[1][root]&0xfffc)
   stale=pages.tables[1][(pages.tables[0][root]&0xfffc)+(vpn&15)*4]
   got=(0,1) if not stale&1 else (0,2) if not stale&2 else (((stale>>8)&255)*256+0x5a,0)
   self.assertNotEqual(got,pages.translate(req['addr'],asid,1))
 def test_reserved_tlb_split(self):
  c=Config('tlb');self.assertEqual([x.entries for x in configurations(c,'reserve')],[11,13])
 def test_v15_every_context_and_generation_is_targeted(self):
  w=generate(Config('tlb'),133)
  self.assertEqual({(p['asid'],p['from_generation']) for p in w['root_invalidation_probes']},{(a,g) for a in range(4) for g in range(3)})
  for i in range(0,24,2):
   warm,inv=w['epochs'][i:i+2]
   self.assertEqual(len(warm['requests']),1)
   self.assertEqual(inv['target_asid'],warm['requests'][0]['aux'])
   self.assertEqual(len(inv['requests']),2)
 def test_v15_extremes_are_nonuniform_and_history_exceeds_v14(self):
  from chip_rl.quality.stress import arithmetic_checks
  c=Config('dot',k=16);w=arithmetic_checks(c,71)
  self.assertGreater(len(w['inputs']),128)
  self.assertEqual(w['expected'][0],16*16384-128)
  self.assertNotEqual((w['inputs'][0]&255),(w['inputs'][0]>>8)&255)
  self.assertTrue(all(x==independent(c,y) for x,y in zip(w['expected'],w['inputs'])))
  self.assertTrue(all(w['release'][i]>=w['release'][i-1] for i in range(1,len(w['release']))))
  self.assertEqual(w['ready'][8:56],[0]*48)
 def test_v15_structures_are_distinct_from_v14(self):
  for task in ('dot','tensor','tlb'):
   c=Config(task)
   self.assertFalse(set(configurations(c,'stress')) & set(configurations(c,True)))
   self.assertFalse(set(configurations(c,'stress')) & set(configurations(c,False)))
 def test_formal_unknown_never_passes(self):
  import tempfile
  from pathlib import Path
  from chip_rl.quality.formal import check
  def fake(cmd,root,label,timeout):
   self.assertIn('-set-assumes',(root/'formal.ys').read_text());return 'No success marker'
  with tempfile.TemporaryDirectory() as td,patch('chip_rl.quality.formal.run',side_effect=fake):
   r=check(design(Config('dot')),'arithmetic',Path(td)/'test')
   self.assertEqual(r['status'],'unproven')
