"""Directed, independent oracle checks for the additive gather reference."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from chip_rl.evaluate import sanitize
from chip_rl.gather_reference import design
from chip_rl.tasks import Config


def write(address, value):
    return 1 | ((address & 255) << 8) | ((value & 0xffffffff) << 16)


def read(mask, addresses):
    return (mask << 4) | sum((address & 255) << (16 + 8 * i)
                             for i, address in enumerate(addresses))


class Oracle:
    def __init__(self, depth):
        self.depth = depth
        self.mem = [0] * depth

    def reset(self):
        self.mem = [0] * self.depth

    def step(self, command):
        if command & 1:
            self.mem[(command >> 8 & 255) % self.depth] = command >> 16 & 0xffffffff
            return 0
        mask = command >> 4 & 15
        words = [self.mem[((command >> (16 + 8*i)) & 255) % self.depth]
                 for i in range(4) if mask & (1 << i)]
        return len(words) | sum(word << (8 + 32*i) for i, word in enumerate(words))


def bench(depth):
    oracle = Oracle(depth)
    lines = []

    def command(x, stall=0):
        expected = oracle.step(x)
        lines.append(f"apply(512'h{x:x}, 256'h{expected:x}, {int(stall)});")

    # Every mask both cold and populated. The populated phase has duplicate
    # addresses and aliases across DEPTH, including 255 -> DEPTH-1.
    for mask in range(16):
        command(read(mask, (0, 0, 255, depth)), mask % 3 == 0)
    for address, value in ((0, 0x10203040), (1, 0xdeadbeef),
                           (depth-1, 0x55aa55aa), (depth, 0xabcdef01),
                           (255, 0x12345678)):
        command(write(address, value), 2)
        command(read(15, (address, address, address, address)), 1)
    for mask in range(16):
        command(read(mask, (0, 0, depth-1, 255)), mask % 4 == 0)
        command(read(mask, (depth, 1, 1 + depth, 255)), mask % 5 == 0)

    first = read(11, (0, 1, depth-1, 255))
    second = write(2, 0x0badcafe)
    first_result = oracle.step(first)
    second_result = oracle.step(second)
    lines.append(f'''@(negedge clk); in_valid=1; in_data=512'h{first:x}; out_ready=1;
      #1; if(in_ready!==1) $fatal(1,"first pipeline acceptance blocked");
      @(posedge clk); #1;
      if(out_valid!==1 || out_data!==256'h{first_result:x}) $fatal(1,"first pipeline response");
      @(negedge clk); in_valid=1; in_data=512'h{second:x}; out_ready=1;
      #1; if(in_ready!==1 || out_data!==256'h{first_result:x})
        $fatal(1,"simultaneous retire and accept blocked");
      @(posedge clk); #1;
      if(out_valid!==1 || out_data!==256'h{second_result:x}) $fatal(1,"second pipeline response");
      @(negedge clk); in_valid=0;
      @(posedge clk); #1;
      if(out_valid!==0) $fatal(1,"pipeline did not drain");''')
    command(read(15, (2, 2 + depth, 2, 2)), 1)

    # Reset cancels a pending output and zeros the entire memory.
    lines.append("reset_pending;")
    oracle.reset()
    for mask in range(16):
        command(read(mask, (0, 1, depth-1, 255)))

    return f'''module tb;
    reg clk=0, rst=1, in_valid=0, out_ready=0;
    reg [511:0] in_data=0;
    wire in_ready, out_valid;
    wire [255:0] out_data;
    candidate #(.DEPTH({depth})) dut(.*);
    always #5 clk=~clk;

    task apply;
      input [511:0] command;
      input [255:0] expected;
      input integer stalls;
      integer k;
      begin
        @(negedge clk); in_valid=1; in_data=command; out_ready=0;
        #1; if(in_ready!==1) $fatal(1,"acceptance blocked");
        @(posedge clk); #1;
        in_valid=0;
        if(out_valid!==1 || out_data!==expected)
          $fatal(1,"response mismatch command=%h got=%h expected=%h",command,out_data,expected);
        for(k=0;k<stalls;k=k+1) begin
          @(negedge clk);
          in_valid=1; in_data=512'hfacefeed000001; out_ready=0;
          #1; if(in_ready!==0 || out_valid!==1 || out_data!==expected)
            $fatal(1,"blocked output changed");
          @(posedge clk); #1;
          if(out_valid!==1 || out_data!==expected) $fatal(1,"stalled output changed");
        end
        @(negedge clk); in_valid=0; out_ready=1;
        @(posedge clk); #1;
        if(out_valid!==0) $fatal(1,"extra output");
      end
    endtask

    task reset_pending;
      begin
        @(negedge clk); in_valid=1; in_data=512'hf0; out_ready=0;
        #1; if(in_ready!==1) $fatal(1,"reset setup blocked");
        @(posedge clk); #1;
        if(out_valid!==1) $fatal(1,"pending output missing");
        @(negedge clk); rst=1; in_data=512'hffffffff000001; out_ready=1;
        #1; if(in_ready!==0 || out_valid!==0) $fatal(1,"reset handshake visible");
        @(posedge clk); #1;
        if(out_data!==0) $fatal(1,"reset register not zero");
        @(negedge clk); rst=0; in_valid=0;
      end
    endtask

    initial begin
      repeat(2) @(posedge clk);
      @(negedge clk); rst=0;
      {chr(10).join(lines)}
      $display("PASS gather decoded depth {depth}");
      $finish;
    end
endmodule'''


class GatherReferenceTest(unittest.TestCase):
    def test_pure_oracle_all_masks_and_aliases(self):
        for depth in (16, 32):
            with self.subTest(depth=depth):
                oracle = Oracle(depth)
                for address, value in ((0, 0x11), (1, 0x22),
                                       (depth-1, 0x33), (depth, 0x44),
                                       (255, 0x55)):
                    self.assertEqual(oracle.step(write(address, value)), 0)
                words = (0x44, 0x44, 0x22, 0x55)
                for mask in range(16):
                    selected = [words[i] for i in range(4) if mask & (1 << i)]
                    expected = len(selected) | sum(v << (8 + 32*i)
                                                    for i, v in enumerate(selected))
                    self.assertEqual(oracle.step(read(mask, (0, depth, 1, 255))), expected)
                oracle.reset()
                for mask in range(16):
                    self.assertEqual(oracle.step(read(mask, (0, depth, 1, 255))),
                                     mask.bit_count())

    def test_source_is_static_mask_decode_and_elastic(self):
        source = design()
        sanitize(source)
        self.assertEqual(len(re.findall(r"4'h[0-9a-f]: begin packed_words", source)), 16)
        self.assertIn("assign in_ready = !rst && (!valid || out_ready);", source)
        self.assertIn("assign out_valid = !rst && valid;", source)
        self.assertIn("else if (!valid || out_ready) begin", source)
        self.assertIn("mem[in_data[8+:8] % DEPTH] <= in_data[16+:32];", source)
        self.assertIn("for (z = 0; z < DEPTH; z = z + 1) mem[z] <= 0;", source)
        self.assertIn("if (rst) begin", source)
        self.assertNotRegex(source, r"result\s*\[.*\+:")
        with self.assertRaises(ValueError):
            design(Config("cache"))

    def test_directed_rtl_against_oracle(self):
        iverilog = shutil.which("iverilog")
        vvp = shutil.which("vvp")
        if not iverilog or not vvp:
            self.skipTest("Icarus Verilog unavailable")
        for depth in (16, 32):
            with self.subTest(depth=depth), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                (path / "candidate.sv").write_text(design(Config("gather", depth=depth)))
                (path / "tb.sv").write_text(bench(depth))
                subprocess.run([iverilog, "-g2012", "-s", "tb", "-o", "tb.vvp",
                                "candidate.sv", "tb.sv"], cwd=path, check=True,
                               capture_output=True, text=True)
                result = subprocess.run([vvp, "tb.vvp"], cwd=path, check=True,
                                        capture_output=True, text=True)
                self.assertIn(f"PASS gather decoded depth {depth}", result.stdout)


if __name__ == "__main__":
    unittest.main()
