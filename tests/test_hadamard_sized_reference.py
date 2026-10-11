"""Pure source-level guards for the additional sized serial reference."""
import hashlib
import json
import unittest
from pathlib import Path

from chip_rl.evaluate import sanitize
from chip_rl.hadamard_int8.rtl import CATALOG, design


FROZEN = json.loads(
    (Path(__file__).parents[1] / "chip_rl/hadamard_int8/frozen_sources.json").read_text()
)


class SizedSerialReferenceTest(unittest.TestCase):
    def test_frozen_references_unchanged(self):
        for name in ("serial_butterfly", "stage_parallel"):
            self.assertEqual(hashlib.sha256(design(name).encode()).hexdigest(), FROZEN[name])

    def test_sized_reference_is_additive_and_sanitized(self):
        self.assertIn("sized_serial_butterfly", CATALOG)
        source = design("sized_serial_butterfly")
        sanitize(source)
        self.assertIn("reg [16*N-1:0] work,next_work;", source)
        self.assertIn("localparam PAIR_W=(N/2>1)?$clog2(N/2):1;", source)
        self.assertIn("localparam LANE_W=(N>1)?$clog2(N):1;", source)
        self.assertIn("localparam STAGE_W=(STAGES>1)?$clog2(STAGES):1;", source)
        self.assertIn("reg [255:0] payload;", source)
        self.assertIn("reg [STAGE_W-1:0] stage;", source)
        self.assertIn("reg [PAIR_W-1:0] pair_index;", source)
        self.assertIn("wire [LANE_W-1:0] a_index", source)
        self.assertIn("wire [LANE_W-1:0] b_index", source)
        self.assertIn("generate if(N>1)begin : butterfly", source)
        self.assertIn("end else begin : single_lane", source)
        self.assertIn("payload<=next_work;state<=RESPONSE;", source)
        self.assertIn("if(N==1)begin", source)

    def test_width_policy(self):
        for n, expected in ((1, (1, 1, 1)), (2, (1, 1, 1)),
                            (4, (1, 2, 1))):
            stages = (n - 1).bit_length()
            actual = (max(1, ((n // 2) - 1).bit_length()),
                      max(1, (n - 1).bit_length()),
                      max(1, (max(1, stages) - 1).bit_length()))
            with self.subTest(n=n):
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
