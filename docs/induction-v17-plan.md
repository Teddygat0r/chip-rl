# V17 prospective induction and reachability plan

Base bd8c08e7377a9b682db32197c3f86892e375418b and all prior artifacts remain preserved. No family, reward, service-gate, external independence, physical or publication change.

Use existing Yosys SAT only. Develop combinational state invariants for the source-bound folded template: reset establishment, occupancy/exclusion, aligned progress, captured-input/shift relationship, legal symbolic products, prefix accumulation, completed output and stall preservation. Seek actual base plus temporal-induction results, not relabeled bounded proofs. Explicitly record the arithmetic cutpoint, assumptions and scope. Independently discharge product-range/linkage evidence and retain unresolved composition.

Use existential reachability witnesses and replay to establish acceptance, progress, completion, stall, resume and reset cancellation. Test bad implementations and deliberately inconsistent harness assumptions; an inductive success with failed reachability cannot qualify as a useful verification result. Prevent candidate formal constraints/monitor shadowing as in v16. Add regression tests for demonstrated defects.

Budget: at most40 SAT commands, each20s solver/35s tool wall, total800s solver allowance; at most12 additional HDL witness/linkage simulations; at most20 affected evaluator calls plus44 aggregate calls. Every timeout/setup failure counts toward its respective launch budget. No proof cache. Existing90s CPU/3GiB address-space/64MiB-file limits apply. Do not start a new evaluation with less than300MiB free. Archive inactive caches with full byte verification if needed, preserving previous deliverables/evidence.

Freeze runtime before final integration; source and installed tests, affected valid/mutant evaluations and all22-family baseline/fault regression. Package exact scripts, witnesses, logs, hashes and local commit. State limitations of finite parameter configurations, reachability bounds, abstraction linkage, environment assumptions and the missing physical flow/PDK.
