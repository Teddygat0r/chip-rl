import unittest
from chip_rl.formal import check_cycle_equivalence,check_elastic
from chip_rl.tasks import Config
from chip_rl.rtl import design
class ContractTests(unittest.TestCase):
    def test_latency_flexible_is_not_cycle_equivalence(self):
        c=Config('elastic',width=8);a=design(c,4);b=design(c,2)
        self.assertEqual(check_cycle_equivalence(a,a)['status'],'bounded_pass')
        self.assertEqual(check_cycle_equivalence(a,b)['status'],'unproven')
        self.assertEqual(check_elastic(b)['status'],'bounded_pass')
if __name__=='__main__':unittest.main()
