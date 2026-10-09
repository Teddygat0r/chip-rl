"""Focused host, contract, and frozen-source checks for BF16 quantization."""
import hashlib,math,random,struct,unittest
from chip_rl.bf16_quant.oracle import quantize,expected,decode_output,pack_input
from chip_rl.bf16_quant.workloads import generate,witness_classes
from chip_rl.bf16_quant.rtl import design
from chip_rl.bf16_quant.spec import Config,NS
from chip_rl.bf16_quant.scoring import score_cases
from chip_rl.evaluate import Rejected,sanitize

def float_check(bits,k,z):
 value=struct.unpack('>f',struct.pack('>I',bits<<16))[0]
 if math.isnan(value):return z
 if math.isinf(value):return -128 if value<0 else 127
 return max(-128,min(127,round(math.ldexp(value,k))+z))

class BF16QuantTest(unittest.TestCase):
 def test_independent_host_subset(self):
  r=random.Random(20261009)
  bits=list(range(0,65536,97))+[0,1,0x7f,0x80,0x7f7f,0x7f80,0xff80,0x7f81,0x7fc0,0xff81,0x3f00,0x3fc0,0x4020,0x4300,0xc300]
  bits.extend(r.randrange(65536) for _ in range(4000))
  for b in bits:
   for k,z in ((-16,-128),(-9,0),(-8,127),(-1,-128),(0,0),(1,127),(15,0)):
    self.assertEqual(quantize(b,k,z),float_check(b,k,z),(b,k,z))
 def test_exact_workloads_and_ignored_bits(self):
  witness_classes()
  for n in NS:
   w=generate(n,17,'development')
   self.assertEqual(w['watchdog_service_budget'],len(w['inputs'])*(4*n+64)+1)
   self.assertGreaterEqual(len(w['inputs']),100)
   self.assertEqual(w['labels'][2],'metadata_k_probe')
   self.assertEqual(w['labels'][4],'metadata_z_probe')
   self.assertNotEqual(expected(w['inputs'][2]^(1<<256),n),w['expected'][2])
   self.assertNotEqual(expected(w['inputs'][4]^(1<<261),n),w['expected'][4])
   for x,y in zip(w['inputs'],w['expected']):
    self.assertEqual(expected(x,n),y)
    self.assertEqual(y>>(8*n),0)
    mask=((1<<(16*n))-1)|(((1<<13)-1)<<256)
    self.assertEqual(expected(x^(((1<<512)-1)^mask),n),y)
   self.assertEqual(decode_output(expected(pack_input((0x7f81,)*n,15,-128),n),n),(-128,)*n)
 def test_source_and_score_gates(self):
  for arch in ('serial','chunked4'):
   src=design(arch);sanitize(src)
   self.assertEqual(hashlib.sha256(src.encode()).hexdigest(),FROZEN[arch])
  def m(n,cells=100,cycles=100,ii=None):
   return {'rtl_mapped_checked':True,'exact_rtl_mapped_checked':True,'exact_vectors_checked':32,
    'cells':cells,'workload_cycles':cycles,'stream_ii_numerator':31*(n+3 if ii is None else ii),'stream_ii_denominator':31}
  cases=[{'N':n,'candidate_verified':True,'baseline_verified':True,'candidate':m(n),'baseline':m(n)} for n in NS]
  self.assertTrue(score_cases(cases)['reward_qualified'])
  self.assertEqual(score_cases(cases)['reward'],0)
  cases[0]['candidate']=m(1,ii=100)
  self.assertFalse(score_cases(cases)['reward_qualified'])
  with self.assertRaises(Rejected):score_cases(cases[:-1])

FROZEN={'serial':'938202845b88fd0c1677e72ade2839b9fee1e6e02812ba80c4e537b836b9fff8','chunked4':'edbc44027e1d0a13b800938a50ce64a9eb8ccdbb06af60409ea95bd27aa82a9e'}
if __name__=='__main__':unittest.main()
