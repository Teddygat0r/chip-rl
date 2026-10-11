# Five-family TRAIN physical calibration checkpoint

**Status: exploratory area-only reference measurement, not physical proxy validation or signoff.** Ten frozen authored-reference RTL points (five same-family/configuration pairs) reached the post-route report stage. The finite pre-route functional checks passed for all ten and the detailed router reported zero route violations for each. This is a single implementation per source, with one TRAIN configuration and two references per family. It establishes a small set of paired routed **standard-cell area** observations. It does not establish a robust ranking, power, achievable core frequency, physical latency, or a trained-policy result.

## Evidence and method

- [`manifest.json`](../evidence/pilot-physical-calibration/manifest.json) freezes the ten source/wrapper/constraint inputs and physical recipe (freeze SHA-256 `0ec4b4ce9424d81494c743fa5c9726be20ea93d5a895dbede651c990cff57ebc`). [`results.json`](../evidence/pilot-physical-calibration/results.json) is the original physical-run output, unmodified. All ten rows report `physical_stage=post_route_report`, `finite_pre_route_checked=true`, `route_completed=true`, and `route_violation_count=0`. The zero is a reported detailed-route violation count, not a deck-level DRC/LVS pass.
- [`joined.json`](../evidence/pilot-physical-calibration/joined.json) copies those physical rows and fills `generic_cells` from the exact-source, exact-family/configuration/reference-label **TRAIN** cases in [`canonical-v2`](../evidence/pilot-reference-panel/canonical-v2/). For non-gather cases the source is `runner_result.metrics.candidate.cells`; for gather, both `runner_result.metrics.replays[*].candidate.cells` values were checked equal before using that value. The original results retain their `generic_cells: null`; neither input was rewritten.
- [`analysis.json`](../evidence/pilot-physical-calibration/analysis.json) is the existing `chip_rl.pilot_analysis.analyze_pilot` output from those ten explicit joined rows. It includes raw paired points, exclusions, counts, ratios and descriptive Spearman correlation, with no p-values or confidence intervals. The separate [`mapped-area-supplement.json`](../evidence/pilot-physical-calibration/mapped-area-supplement.json) is **post-run extraction** from hashed ORFS `synth_stat.txt` reports, not a measurement returned in the original runner field (`metrics.mapped_stdcell_area_um2` remains null).
- The measurement used Nangate45, a fixed 140 × 140 μm die and 10..130 μm core bounds, a requested placement density of 0.55, a 20 ns clock, 4 ns input and output delays, and timed reset. Synthesis and detailed route used the frozen physical recipe. The fixed core bounds do **not** mean fixed effective placement density. There was no GDS generation.

## All ten observed points

Area is final reported standard-cell instance area in μm². The last column is mapped area from the **supplement**, shown separately from the original physical result. `Req.` and `Eff.` are requested and reported effective placement density. All rows passed finite pre-route checks and completed detailed route; all have **reported** route violation count 0.

| Family / config | Reference | Generic cells | Post-route area μm² | Setup slack ns | Route violations | Req. density | Eff. density | Case wall s | Case CPU s | Supplement mapped area μm² |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gather DEPTH 16 | legacy_baseline | 4,614 | 8,996.92 | 11.7869 | 0 | 0.55 | 0.67 | 222.457 | 391.164 | 8,955.954 |
| gather DEPTH 16 | static_decoded | 4,863 | 8,988.14 | 11.7600 | 0 | 0.55 | 0.67 | 243.664 | 436.225 | 9,070.334 |
| mshr ENTRIES 2 | ring | 1,097 | 4,337.13 | 11.5560 | 0 | 0.55 | 0.55 | 82.752 | 132.316 | 4,072.726 |
| mshr ENTRIES 2 | shift | 1,077 | 4,241.90 | 11.5405 | 0 | 0.55 | 0.55 | 74.547 | 117.355 | 3,937.598 |
| sparse24 G 2 | serial | 8,266 | 10,129.30 | 11.8141 | 0 | 0.55 | 0.78 | 274.898 | 482.316 | 10,163.860 |
| sparse24 G 2 | pipeline | 8,713 | 11,010.00 | 11.7029 | 0 | 0.55 | 0.84 | 280.547 | 477.035 | 11,045.916 |
| block_quant N 4 | serial | 2,223 | 2,136.25 | 11.8334 | 0 | 0.55 | 0.55 | 76.306 | 112.246 | 2,016.812 |
| block_quant N 4 | chunked4 | 2,935 | 4,129.65 | 11.8058 | 0 | 0.55 | 0.55 | 145.729 | 243.226 | 4,147.206 |
| hadamard_int8 N 4 | serial_butterfly | 4,717 | 5,210.94 | 11.8432 | 0 | 0.55 | 0.55 | 153.251 | 261.416 | 5,093.102 |
| hadamard_int8 N 4 | sized_serial_butterfly | 1,379 | 2,042.88 | 11.8571 | 0 | 0.55 | 0.55 | 68.482 | 104.288 | 1,949.248 |

Summed case resource accounting is **1,622.633 s wall** and **2,757.587 s CPU**, verified from the ten original results. Cases were run concurrently, so the summed case-wall figure is not end-to-end elapsed time, and neither number is a universal per-candidate evaluation cost. The range here is 68.482–280.547 s wall and 104.288–482.316 s CPU per case under this toolchain and selected designs. Reported peak RSS, stage resources, floorplan geometry, routed wirelength, slack and other fields remain in the original results; missing mapped area in those original rows is not zero.

## Paired area comparison

Ratios use the named alternative divided by the baseline in the same family/configuration. Four of five **directions** of generic-cell and post-route area changes agree. Magnitudes are not interchangeable.

| Family / config | Baseline → alternative | Generic-cell ratio | Post-route area ratio | Direction |
|---|---|---:|---:|---|
| gather DEPTH 16 | legacy_baseline → static_decoded | 1.0540 | 0.9990 | Disagree |
| mshr ENTRIES 2 | ring → shift | 0.9818 | 0.9780 | Agree |
| sparse24 G 2 | serial → pipeline | 1.0541 | 1.0869 | Agree |
| block_quant N 4 | serial → chunked4 | 1.3203 | 1.9331 | Agree |
| hadamard_int8 N 4 | serial_butterfly → sized_serial_butterfly | 0.2923 | 0.3920 | Agree |

Gather's routed areas are **8,996.92 → 8,988.14 μm²**, a difference of −8.78 μm² (−0.10%) in a single run; this near-tie must not be described as a robust alternative ranking. Its post-run mapped-area supplement actually increases from 8,955.954 to 9,070.334 μm², so mapped and routed values have different ordering here. Hadamard's **5,210.94 → 2,042.88 μm²** (−60.8%) is a much larger observed area change, but still only one N=4 pair and one physical run per source. Sparse serial and pipeline have effective densities 0.78 and 0.84, respectively, under the same 0.55 request and fixed core bounds; gather's two runs both report 0.67. These density differences matter when interpreting the pair.

The descriptive pooled Spearman rank correlation of generic cells with post-route area is **ρ = 0.7818 (n=10)**. Each of the five families contributes only two points at one TRAIN parameter. Across families, circuit size and interface/architecture differ; pooling is size-confounded and **is not calibration evidence**. Within a two-point stratum, a rank correlation conveys only direction and has no useful precision. No sampling uncertainty, repeated tool-seed variation, or multi-configuration ranking stability was measured. The three-point-per-family, multiple-configuration physical validation proposed in the [experiment protocol](pilot-experiment-protocol.md) remains pending.

## Timing scope and claim boundary

[`critical-path-scope.json`](../evidence/pilot-physical-calibration/critical-path-scope.json) records the exact first maximum-setup-path startpoint and endpoint and SHA-256 of every private `6_finish.rpt`, without exposing private working paths. Every one of the ten first max setup paths is **input-port to output-port**: seven start at `rst`, both MSHR cases start at `req_addr[15]`, and sparse24 pipeline starts at `out_ready`. Their endpoints are `in_ready`, `out_valid` or `req_ready` as recorded. With the deliberately loose **20 ns clock and 4 ns external input/output delays**, these I/O paths dominate the reported setup metrics. The approximately 11.5–11.9 ns setup slacks in the table therefore **cannot** be used to claim core performance correlation, physical latency or Fmax. A timing study would need a separately justified critical-path and period analysis under predeclared constraints. Reported zero route violations and finite pre-route simulation do not replace post-route functional checks, formal equivalence, GDS, reference-deck DRC, LVS or power measurement; none of those latter checks were completed here.

## Reproduction pins and remaining gates

The benchmark generic-cell measurements used the separate Debian-packaged **Yosys 0.52-2** toolchain from the frozen benchmark setup (Yosys package SHA-256 `c950e58a1f554546a91602e5124eb05019a92040e57b0aaa43cf33b032ee9c40`; Yosys-ABC package SHA-256 `f54c92c5ce88959f6aedc71c7b01eaf2b39d6c8c3e5f02784b6ce24736dc50e4`). Physical synthesis used **OSS CAD Suite 2026-10-08, Yosys 0.69+260** (git `dcd59343b`) and **OpenROAD 26Q2-1164-g08f67ee5ec**. This is not an identical synthesis mapping recipe: Yosys version, ABC/technology mapping and the Nangate45 physical flow can contribute to disagreements between generic-cell counts and standard-cell area. The physical manifest pins executable and flow inputs by hash.

Portable official source archives and verified download SHA-256 from the local setup provenance:

| Component | Official download | SHA-256 |
|---|---|---|
| OpenROAD Flow Scripts commit `87b01b74b92d6e77edcdbe86949ee7eb6017ac7d` | [GitHub archive](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/archive/87b01b74b92d6e77edcdbe86949ee7eb6017ac7d.tar.gz) | `df2b06ac766d9d32a77fc35e79588cab18e66d38e41c8c345bdcec7e1c1934fd` |
| OpenROAD Ubuntu 24.04 `26Q2-1164-g08f67ee5ec` | [Precision Innovations package](https://vaultlink.precisioninno.com/api/releases/26Q2-1164-g08f67ee5ec/openroad_26Q2-1164-g08f67ee5ec_amd64-ubuntu-24.04.deb/download) | `f3f1eeaa18f327503f72cc45dcef5b1514ec2e89726ec53b4553bf4f951168a3` |
| OSS CAD Suite linux-x64 `2026-10-08` | [YosysHQ archive](https://github.com/YosysHQ/oss-cad-suite-build/releases/download/2026-10-08/oss-cad-suite-linux-x64-20261008.tgz) | `8fa59d93d6cadbbee352077c059f2c5b72cda301e4508d9064a23d1ec11579c7` |
| `tcl-tclreadline` 2.3.8-2build2 (Ubuntu 24.04 runtime dependency) | [Ubuntu package](https://archive.ubuntu.com/ubuntu/pool/universe/t/tclreadline/tcl-tclreadline_2.3.8-2build2_amd64.deb) | `7f61dca1a7f55c445babfd2c718ff5359de8a61288125089c1c8a9e788c11f00` |
| `libpython3.12t64` 3.12.3-1ubuntu0.17 (Ubuntu 24.04 runtime dependency) | [Ubuntu package](https://archive.ubuntu.com/ubuntu/pool/main/p/python3.12/libpython3.12t64_3.12.3-1ubuntu0.17_amd64.deb) | `0d29f4763eb95b8a4283a4aca3ef1d9658629c618be1778def41bdc31be12b46` |

This checkpoint does not complete model-difficulty measurement, weight-updated policy training, independent human RTL review, or multi-point physical proxy validation. None of the reported observations is a post-route functional/formal proof or a PPA signoff. No model calls, new design iterations, physical reruns or publication are part of this checkpoint.
