# Requant reset repair: approved bounds

Preserve f9d7137, v24/728e24a and v25/923b849 unchanged in their original worktrees. This branch repairs the demonstrated reset false acceptance before expansion. Numerical semantics, baseline, workload/service thresholds and reward weights remain frozen.

Fresh approved caps: 48 requant evaluator calls, 120 synthesis calls, 512 simulations, plus one separate 47-call inherited/layout/softmax aggregate. Existing local tools and per-tool limits only; at most two concurrent evaluations. Reserve a fresh 8000 independent numerical-comparison allowance (7200 boundary comparisons plus bounded unit checks). Stop before caps or below 300MiB free. No push/upload, spending, credentials or security changes.

Add unscored capacity-adaptive cancellation: first accept with consumer ready, then offer more work with consumer blocked without requiring additional acceptance, assert one reset edge with poisoned input data/mask/valid and drain for ghost responses. Exercise both before and after scored work. Add poisoned cold/idle reset probes. Retain strict trace validation and measured acceptance counts so single-slot, ready-gated and multi-slot implementations are distinguished without prescribing capacity. Preserve exact escaped RTL and direct two-pending positive/negative controls.

Planned final checks: five valid architectures across development/heldout (10), all fourteen existing corruptions plus the escaped reset source (15), installed API (4), two exact replays (2), numerical boundaries and direct reset controls, 188+ unit tests, and the 47-call aggregate. Remaining evaluator allowance is reserved for demonstrated failures or regression diagnosis, not threshold tuning.
