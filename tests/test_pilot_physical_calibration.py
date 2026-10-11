"""Freeze-first physical method tests.  These never start an ORFS job."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import pilot_physical_calibration as physical


class PhysicalCalibrationTests(unittest.TestCase):
    def test_exact_train_panel_and_source_identity(self):
        self.assertEqual(len(physical.CASES), 10)
        self.assertEqual(len({physical.case_id(*row) for row in physical.CASES}), 10)
        self.assertEqual({f for f, _, _ in physical.CASES},
                         {"gather", "mshr", "sparse24", "block_quant", "hadamard_int8"})
        from chip_rl.tasks import Config as GatherConfig
        from chip_rl.rtl import design as gather_design
        from chip_rl.memory.spec import Config as MemoryConfig
        from chip_rl.memory.rtl import design as memory_design
        self.assertEqual(physical.source_for("gather", 16, "legacy_baseline"),
                         gather_design(GatherConfig("gather")))
        self.assertEqual(physical.source_for("mshr", 2, "ring"),
                         memory_design(MemoryConfig("mshr"), "ring"))
        for family, n, label in physical.CASES:
            self.assertTrue(physical.source_for(family, n, label).startswith("module candidate"))
        with self.assertRaises(ValueError):
            physical.source_for("hadamard_int8", 8, "serial_butterfly")

    def test_compressed_wrapper_bits_and_full_adapter(self):
        expected = {"gather": (48, 136), "sparse24": (174, 32),
                    "block_quant": (64, 36), "hadamard_int8": (32, 64)}
        for family, (iw, ow) in expected.items():
            n = 16 if family == "gather" else 2 if family == "sparse24" else 4
            wrap = physical.wrapper(family, n)
            adapter = physical.mapped_candidate_adapter(family)
            self.assertIn(f"[{iw-1}:0] in_data", wrap)
            self.assertIn(f"[{ow-1}:0] out_data", wrap)
            self.assertIn("[511:0] in_data", adapter)
            self.assertIn("module candidate", adapter)
        self.assertIn("in_data[173:112],336'b0,in_data[111:0]",
                      physical.wrapper("sparse24", 2))
        self.assertIn("full_out[131:128],full_out[31:0]",
                      physical.wrapper("block_quant", 4))
        mshr = physical.wrapper("mshr", 2)
        self.assertIn("[127:0] resp_data", mshr)
        self.assertIn("[15:0] req_addr", mshr)
        self.assertNotIn("full_out", mshr)

    def test_source_wrapper_elaborates_all_cases(self):
        iverilog = shutil.which("iverilog") or str(physical.TOOLS_ROOT / "oss-cad-suite/bin/iverilog")
        if not Path(iverilog).is_file():
            self.skipTest("Icarus not installed")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            for family, n, label in physical.CASES:
                src = path / "design.v"
                src.write_text(physical.source_for(family, n, label) + "\n" + physical.wrapper(family, n))
                subprocess.run([iverilog, "-g2012", "-s", "physical_top", "-o", str(path / "a.vvp"),
                                str(src)], check=True, capture_output=True, text=True)

    def test_constraints_fixed_and_reset_timed(self):
        sdc = physical.constraints()
        self.assertIn("-period 20", sdc)
        self.assertIn("set_input_delay 4 -clock clk [all_inputs -no_clocks]", sdc)
        self.assertNotIn("get_ports rst", sdc)
        self.assertIn("set_output_delay 4", sdc)
        config = physical.config()
        self.assertIn("export PLACE_DENSITY = 0.55", config)
        self.assertIn("export DIE_AREA = 0 0 140 140", config)
        self.assertIn("export CORE_AREA = 10 10 130 130", config)
        self.assertIn("export NUM_CORES = 2", config)

    def test_freeze_detects_edit_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "evidence"
            # Uses only hashable tool inputs; no physical flow is run.
            try:
                manifest = physical.freeze(root)
            except FileNotFoundError as exc:
                self.skipTest(str(exc))
            self.assertEqual(manifest["freeze_sha256"], physical.verify_freeze(root)["freeze_sha256"])
            self.assertEqual(len(manifest["cases"]), 10)
            with self.assertRaises(FileExistsError):
                physical.freeze(root)
            case = root / "cases" / manifest["cases"][0]["case"]
            with (case / "constraints.sdc").open("a") as stream:
                stream.write("# illegal after freeze\n")
            with self.assertRaises(ValueError):
                physical.verify_freeze(root)

    def test_missing_metrics_remain_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            metrics = physical.extract_metrics(run)
            self.assertIsNone(metrics["setup_slack_ns"])
            self.assertIsNone(metrics["physical_stdcell_area_um2"])
            self.assertIsNone(metrics["route_violation_count"])
            self.assertIsNone(metrics["reported_path_delay_ns"])
            (run / "5_2_route.json").write_text(json.dumps({"detailedroute__route__drc_errors": 2}))
            (run / "6_report.json").write_text(json.dumps({"finish__design__instance__area": 350.5,
               "finish__timing__setup__ws": -0.25, "finish__timing__hold__ws": 0.05}))
            metrics = physical.extract_metrics(run)
            self.assertEqual(metrics["route_violation_count"], 2)
            self.assertEqual(metrics["physical_stdcell_area_um2"], 350.5)
            self.assertEqual(metrics["setup_slack_ns"], -0.25)
            self.assertEqual(metrics["hold_slack_ns"], 0.05)

    def test_density_is_distinct_from_utilization_and_nonfinite_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "3_3_place_gp.json").write_text(json.dumps({
                "globalplace__design__instance__utilization": 0.81}))
            self.assertIsNone(physical.extract_metrics(run)["effective_place_density"])
            (run / "3_3_place_gp.log").write_text("Placement density is 0.60, computed from lower bound\n")
            self.assertEqual(physical.extract_metrics(run)["effective_place_density"], 0.60)
            self.assertIsNone(physical._number({"value": float("nan")}, "value"))
            self.assertIsNone(physical._number({"value": "inf"}, "value"))

    def test_orfs_stage_resource_time_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "route.log"
            log.write_text("Elapsed time: 0:04.26[h:]min:sec. CPU time: user 4.08 sys 0.17 (99%). Peak memory: 671508KB.\n")
            self.assertEqual(physical._stage_resource(log), {
                "elapsed_s": 4.26, "cpu_s": 4.25, "peak_rss_kib": 671508})
            log.write_text("Elapsed time: 01:30:00[h:]min:sec. CPU time: user 3000 sys 150 (58%). Peak memory: 9667132KB.\n")
            self.assertEqual(physical._stage_resource(log), {
                "elapsed_s": 5400.0, "cpu_s": 3150.0, "peak_rss_kib": 9667132})

    def test_private_results_rejected_inside_repo(self):
        with self.assertRaises(ValueError):
            physical.measure(Path("/does/not/matter"), physical.REPO / "private-bad")


if __name__ == "__main__":
    unittest.main()
