import json
import math
import tempfile
import unittest
from pathlib import Path

from chip_rl.pilot_analysis import analyze_pilot, average_ranks, spearman_rank_correlation
from scripts.analyze_pilot_physical import main


def row(name="base", *, family="gather", config=16, cells=10, area=100.0,
        baseline=False, sha="a" * 64, **changes):
    result = {
        "family": family, "config": config, "reference_name": name,
        "source_sha256": sha, "generic_cells": cells,
        "physical_stdcell_area_um2": area, "physical_stage": "routed",
        "finite_pre_route_checked": True, "route_completed": True,
        "is_baseline": baseline, "route_violation_count": 0,
    }
    result.update(changes)
    return result


class RankTests(unittest.TestCase):
    def test_tie_average_ranks(self):
        self.assertEqual(average_ranks([30, 10, 10, 20]), [4, 1.5, 1.5, 3])
        self.assertAlmostEqual(spearman_rank_correlation([1, 1, 2], [1, 2, 2]), .5)

    def test_perfect_and_reverse(self):
        self.assertEqual(spearman_rank_correlation([1, 2, 3], [4, 5, 6]), 1)
        self.assertEqual(spearman_rank_correlation([1, 2, 3], [6, 5, 4]), -1)
        self.assertIsNone(spearman_rank_correlation([1, 1], [2, 3]))
        self.assertIsNone(spearman_rank_correlation([1], [2]))
        self.assertIsNone(spearman_rank_correlation([], []))
        with self.assertRaises(ValueError):
            spearman_rank_correlation([1], [1, 2])
        with self.assertRaises(ValueError):
            spearman_rank_correlation([1, math.inf], [1, 2])


class AnalysisTests(unittest.TestCase):
    def test_valid_pairs_and_pooled_warning(self):
        rows = [
            row(baseline=True), row("smaller", cells=5, area=50, sha="b" * 64),
            row("tie", cells=10, area=90, sha="c" * 64),
            row("other_family", family="mshr", config=2, cells=25, area=200,
                baseline=True, sha="d" * 64),
            row("opposite", family="mshr", config=2, cells=20, area=220,
                sha="e" * 64),
        ]
        result = analyze_pilot(rows)
        self.assertEqual(result["denominators"]["attempts"], 5)
        self.assertEqual(result["pooled_association"]["family_counts"], {"gather": 3, "mshr": 2})
        self.assertIn("confounded", result["pooled_association"]["warning"])
        self.assertEqual(len(result["pairs"]), 3)
        by_name = {p["candidate_reference_name"]: p for p in result["pairs"]}
        self.assertEqual(by_name["smaller"]["cell_ratio"], .5)
        self.assertEqual(by_name["smaller"]["area_ratio"], .5)
        self.assertTrue(by_name["smaller"]["direction_agrees"])
        self.assertIsNone(by_name["tie"]["direction_agrees"])
        self.assertEqual(by_name["tie"]["direction_status"], "tie")
        self.assertFalse(by_name["opposite"]["direction_agrees"])
        self.assertIn("not independent", " ".join(result["notes"]))

    def test_invalid_and_incomplete_attempts_keep_denominator(self):
        invalid = row("bad", cells=0, area=float("nan"), sha="bad", route_completed=False,
                      finite_pre_route_checked=False)
        missing = row("missing", sha="c" * 64)
        del missing["generic_cells"]
        rows = [row(baseline=True), row("ok", sha="b" * 64), invalid, missing,
                row("unrouted", sha="d" * 64, route_completed=False)]
        result = analyze_pilot(rows)
        self.assertEqual(result["denominators"]["attempts"], 5)
        self.assertEqual(result["denominators"]["routed_included"], 2)
        self.assertEqual(result["denominators"]["excluded"], 3)
        self.assertEqual(result["pooled_association"]["n"], 2)
        self.assertIn("invalid_generic_cells", result["attempts"][2]["exclusion_reasons"])
        self.assertIn("finite_pre_route_not_checked", result["attempts"][2]["exclusion_reasons"])
        self.assertIn("missing_generic_cells", result["attempts"][3]["exclusion_reasons"])
        json.dumps(result, allow_nan=False)

    def test_missing_duplicate_baseline_and_same_source(self):
        missing = analyze_pilot([row("alt", sha="b" * 64)])
        self.assertEqual(missing["pairs"], [])
        self.assertEqual(missing["pair_diagnostics"][0]["reason"], "missing_baseline")
        duplicate = analyze_pilot([
            row("a", baseline=True), row("b", baseline=True, sha="c" * 64),
            row("alt", sha="b" * 64),
        ])
        self.assertEqual(duplicate["pairs"], [])
        self.assertEqual(duplicate["pair_diagnostics"][0]["reason"], "duplicate_baseline")
        same = analyze_pilot([row(baseline=True), row("alt", sha="a" * 64)])
        self.assertEqual(same["pairs"], [])
        self.assertEqual(same["pair_diagnostics"][0]["reason"], "same_source_as_baseline")

    def test_route_violations_are_visible_but_not_misclassified(self):
        rows = [row(baseline=True, route_violation_count=0),
                row("violating", sha="b" * 64, route_violation_count=3),
                row("unknown", sha="c" * 64)]
        del rows[2]["route_violation_count"]
        result = analyze_pilot(rows)
        self.assertEqual(result["denominators"]["route_completed_attempts"], 3)
        self.assertEqual(result["denominators"]["violation_free_completed_attempts"], 1)
        self.assertEqual(result["denominators"]["completed_attempts_with_violations"], 1)
        self.assertEqual(result["denominators"]["route_violation_count_known_completed_attempts"], 2)
        self.assertEqual(result["pairs"][0]["candidate_route_violation_count"], 3)
        self.assertIsNone(result["pairs"][1]["candidate_route_violation_count"])

    def test_invalid_optional_values_and_constant_correlation(self):
        result = analyze_pilot([
            row(baseline=True), row("same", cells=10, area=90, sha="b" * 64),
            row("bad_slack", sha="c" * 64, setup_slack_ns=float("inf")),
            row("bad_violation", sha="d" * 64, route_violation_count=-1),
        ])
        self.assertIsNone(result["pooled_association"]["spearman_rho"])
        self.assertEqual(result["denominators"]["excluded"], 2)

    def test_null_optional_values_are_unknown_not_failed(self):
        result = analyze_pilot([
            row(baseline=True, setup_slack_ns=None, route_violation_count=None,
                elapsed_s=None),
            row("other", sha="b" * 64, cells=9, area=80,
                setup_slack_ns=None, route_violation_count=None, elapsed_s=None),
        ])
        self.assertEqual(result["denominators"]["routed_included"], 2)
        self.assertEqual(result["denominators"]["route_violation_count_known_completed_attempts"], 0)
        self.assertIsNone(result["pairs"][0]["candidate_route_violation_count"])

    def test_mixed_stages_not_correlated_or_paired(self):
        result = analyze_pilot([
            row(baseline=True, physical_stage="post_route"),
            row("different_stage", sha="b" * 64, physical_stage="global_route"),
        ])
        self.assertEqual(result["pairs"], [])
        self.assertEqual(result["pair_diagnostics"][0]["reason"], "physical_stage_mismatch")
        self.assertIsNone(result["pooled_association"]["spearman_rho"])
        self.assertEqual(result["pooled_association"]["undefined_reason"], "mixed_physical_stages")

    def test_cli_reads_only_explicit_input(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / "joined.json", Path(temp) / "analysis.json"
            source.write_text(json.dumps({"rows": [row(baseline=True),
                                                   row("alt", sha="b" * 64)]}))
            self.assertEqual(main([str(source), "--output", str(output)]), 0)
            report = json.loads(output.read_text())
            self.assertEqual(report["denominators"]["attempts"], 2)


if __name__ == "__main__":
    unittest.main()
