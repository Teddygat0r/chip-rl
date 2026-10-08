# Frozen v22 findings, before fixes

Pinned source191e6c0948501da48affad743fe715f9b0ecbbb5, wheel02a724ffb40cff6a383eba8e4b4a23ef17cb07c138b8e0f819e8a0274d25e32a, baseline RTL ae16a5aad12d77493b837bf21efb0a8cc875af59699bd2bd726343766a31ff8b, tool fingerprint9f09818abb592bcd94083f044465209e067389983ec3f90f93ca78a8070e7ac8. Toolchain remains Icarus12/Yosys0.52/ABC. All evidence in this report precedes runtime changes.

The supplied review was independently authored but is now visible to the implementer. This is a review-guided audit, not hidden or independently executed evaluation.

## Contract conflict and numerical reference

The review's equal-logit +16/-16, L1=64 and normalization=15 acceptance vectors pass their individual numerical bounds. They fail v22's separate equal-logit spread<=1 unit requirement. +17/-17 and L1=65 fail numerical accuracy; normalization=16 fails normalization. It is impossible to accept the former vectors under the complete existing contract without changing the tie rule. A clarification was requested; pending an explicit revision, retain the rule and test each numerical gate separately.

N means structural lane count, not active count. A singleton output4081 at N16 passes the published sum allowance15, while the same output at N2 fails allowance1. This is a permissive but explicit contract, not an oracle defect. Empty mask requires exactlyzero output, independent of the sum tolerance. The unrounded ideal threshold is used: the near-boundary two-lane examples correctly distinguish actual ideal error from error after rounding the ideal.

A separately implemented140-digit Taylor exponential with argument divided by256 and eight squarings, then120-digit normalization, agrees with the80-digit Decimal.exp oracle on3598 vectors. These include all511 signed raw differences with representative legal offsets and positions, every mask cardinality0..16 at16 rotations, ties and signed extremes. No Decimal.exp, math.exp or candidate LUT is used in the cross-reference. Maximum difference4.1808873286227738345875461835183671400187e-80. No arithmetic-oracle defect was demonstrated.

## New demonstrated gaps

* `late449`: synthesizable RTL returns zero after448 accepted transactions. Frozen v22 accepts it because each scored batch resets by448. A separate continuous1024-transaction N2 RTL/mapped test passes the baseline and rejects the identical mutant for numerical accuracy.448 is only a campaign limit, not a valid circuit lifetime.
* `stall-edge`: a reset qualified by `(!out_valid_internal || previous_reset)` passes frozen v22's three-edge idle/stall resets and single-edge busy reset. It violates cancellation on one reset edge when a completed response is held. Preserve this old acceptance and require final rejection with single-edge stall coverage.
* Direct checker accepts extra high bits above the256-bit output and negative packed integers after masking. A real256-bit HDL port cannot emit these encodings, so this is a host-boundary validation defect, not a demonstrated source-only HDL escape.
* Direct log fault injection accepts duplicate OUT records, malformed extra OUT records, a wrong declared transaction count and a substring masquerading as DRAIN_PASS. Missing outputs and PASS-only text are already rejected. These parser weaknesses are defense-in-depth findings; source restrictions prohibit candidate $display/system tasks, and no candidate-mediated log forgery is claimed.

## Existing overlap and remaining tests

V22 already covers all nonnegative deltas0..255 at two legal offsets, four original/fine-fast valid designs plus rounding/underflow alternatives, ordering/ties/extrema, invalid-cycle poison, three-cycle resets, a one-edge busy reset, output stalls, duplicate drains and disjoint lane counts. Gaps prioritized here are negative orientations/position variations, systematic mask cardinalities, parser boundaries, one-edge idle/stall/counter resets and continuous streams beyond448. Metamorphic checks must enforce the existing shift allowance2 units and numerical contract without adding bit-identity requirements between different approximations or transformed inputs. Exact RTL/mapped equality remains appropriate for the same circuit and stimulus.

Actual isolation is limited: uid1000 can read/write trusted oracle/specification, private seeds/results and cache. Repository tooling does not create a separate uid or filesystem namespace for candidates. Source-only actions, restricted syntax, fixed tool invocations, trimmed child environment, resource limits and private directory modes exist, but same-uid shell access defeats file separation. No security settings were changed; do not describe this as a secure untrusted-agent sandbox.
