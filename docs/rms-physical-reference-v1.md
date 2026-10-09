# N=4 integer RMS physical reference comparison

This is a **bounded physical reference comparison** of the existing frozen `serial` and `serial_comb_root` RTL at N=4, under an identical Nangate45/ORFS flow, fixed die/core footprint and a deliberately generous 100 ns clock. It does not change any family API, qualification gate, reward or reference source.

| Reported measurement | Serial | Serial combinational root |
|---|---:|---:|
| Final standard-cell area (µm²) | 7,794.86 | 9,087.09 |
| Final cell/core utilization | 55.3% | 64.5% |
| Worst setup slack (ns) | 59.7922 | 59.8555 |
| ORFS reported critical-path delay (ns) | 20.2078 | 20.1445 |
| Worst hold slack (ns) | 0.09623 | 0.10459 |
| OpenROAD detailed-route violations | 0 | 0 |
| OpenROAD antenna net/pin violations | 0/0 | 0/0 |
| KLayout reference-deck DRC | Timed out, incomplete | Timed out, incomplete |

The comb-root design has 16.58% more final standard-cell area. The 100 ns setup constraint is met in both runs, but this is not a maximum-frequency or equal-effective-density study: OpenROAD raised the requested 0.55 placement density to effective 0.60 and 0.70, respectively, inside the same core. Worst setup slack and the separately reported critical-path delay are distinct report fields.

Both flows completed final GDS. Before routing, each source wrapper and Nangate45-mapped wrapper passed 39 independent exact-oracle 64-bit vectors with blocked-output stability checks. These checks were **pre-route**. OpenROAD route/antenna counts of zero do not establish reference-deck DRC clearance. Both KLayout deck runs remained CPU-active until a 30-minute cap and produced no DRC report. There was no LVS, SDF simulation, post-route functional equivalence, foundry signoff, power measurement or clock-frequency sweep.

The [full bounded report](../evidence/rms-physical-reference-v1/README.md), [metrics](../evidence/rms-physical-reference-v1/metrics.json), [frozen sources, wrapper and configuration](../evidence/rms-physical-reference-v1/), and [reproduction notes](../evidence/rms-physical-reference-v1/REPRODUCE.md) are retained as compact public evidence. The completed layout databases and timeout logs are in the separate owner-only replay archive. Tool versions, source hashes and the fixed constraints are in the evidence bundle. The existing 240/240 source-test and installed-wheel checks predate these documentation-only additions and were not rerun.
