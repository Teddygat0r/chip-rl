# N=4 integer RMS physical reference comparison (final bounded run: both KLayout reference DRC checks timed out)

## Fixed inputs

- Own cloud workspace only: `chip-rl-physical-work/`. No source-tree changes or external publication.
- Frozen generated sources: serial SHA256 `0a7241139699cbd77852761dc6969fade0ccaf1a71b9baef09590b5f581cb7a3`; serial_comb_root SHA256 `c7f72191ad6883f3543594544143517b88728883f32520f0b776a289d258d873`.
- Same wrapper: four 16-bit active lanes exposed as 64-bit input/output, upper candidate input tied to zero and inactive candidate output omitted; ready-valid/clk/rst preserved. SHA256 `d01707b0f405d215ed80262fd6d7dc86580c07ad1090b77c390ff635509baeeb`.
- Same Nangate45 PDK/reference flow at ORFS `87b01b74b92d6e77edcdbe86949ee7eb6017ac7d`, official OpenROAD `26Q2-1164-g08f67ee5ec`, official OSS CAD Suite 2026-10-08/Yosys `0.69+260-gdcd59343b`, Debian KLayout `0.30.0`.
- Requested die `0 0 140 140` µm and core `10 10 130 130` µm, actual legal-site core `(10.070,11.200)-(129.960,128.800)` µm, identical for both. `PLACE_DENSITY=0.55`, clock 100 ns, input/output delays each 20 ns, 2 CPU threads and 3 GB RLIMIT_AS virtual-address-space cap per process (which also bounds RSS).
- As-run source, wrapper, configuration and official tool archive SHA256 values are in `as_run_hashes.sha256`. The published variant Makefiles are path-rebased copies, with the same design settings and different SHA256 from the original location-specific Makefiles.

## Verification before and after physical flow

- Both source wrappers and both Nangate45-mapped wrappers passed 39 independent exact-oracle 64-bit vectors, with three-cycle blocked-output stability checks. These were pre-route functional smokes.
- Both ORFS flows completed final GDS with identical nominal constraints. No post-route netlist equivalence, SDF simulation, LVS, or foundry signoff was attempted.

| Metric | Serial | Serial combinational root |
|---|---:|---:|
| Final standard-cell area, µm² | 7794.86 | 9087.09 |
| Final cell/core utilization | 55.3% | 64.5% |
| Worst setup slack, ns | 59.7922 | 59.8555 |
| Setup TNS, ns | 0 | 0 |
| ORFS reported critical-path delay, ns | 20.2078 | 20.1445 |
| Worst hold slack, ns | 0.09623 | 0.10459 |
| OpenROAD detailed-route violations | 0 | 0 |
| OpenROAD antenna net/pin violations | 0/0 | 0/0 |
| ORFS through-finish elapsed, s | 200 | 226 |
| ORFS peak process memory, MB | 1178 | 1026 |
| Final GDS bytes | 4309326 | 5128648 |
| Reference-deck KLayout DRC | timed out / incomplete | timed out / incomplete |

The final standard-cell area is 16.58% greater for comb-root. The generous 100 ns constraint is met in both runs. Worst setup slack and the separately reported critical-path delay are different report fields and should not be conflated as a clock-frequency result. OpenROAD automatically raised *effective* placement targets from the requested 0.55 to 0.60 (serial) and 0.70 (comb-root) because of their different utilization in the same core. This is a fixed-footprint comparison, not an equal-effective-density study.

The first serial KLayout GDS conversion and DRC attempt had a missing local Ruby library path. The corrected Ruby runtime regenerated the GDS with no errors, but the first corrected DRC was interrupted after about 6m40s of no log growth. A monitored retry showed sustained CPU use in the same FreePDK45 ACTIVE.1 Euclidean-width operation, then reached the 30-minute wall cap (~1,805 s and ~1,802 cumulative CPU-seconds, ~520 MB sampled process-tree RSS) without producing a deck report. The comb-root deck was identically capped and also stayed CPU-active at the same ACTIVE.1 check: 1,805.3 s total, ~1,798 CPU-seconds at the cap, and 559.8 MB peak sampled process-tree RSS. Neither deck produced a `.lyrdb` report. Both reference-deck results are timed out/incomplete. Neither an incomplete deck run nor an OpenROAD zero-violation report establishes reference-deck DRC clearance.

## Reproduction

See `REPRODUCE.md` for the fixed commands, binary pins and stage limits. The source, wrapper, SDC, common Makefile, testbench, and vectors are included. Tool binaries, bulk logs and generated layout databases are intentionally excluded from this public evidence bundle.
