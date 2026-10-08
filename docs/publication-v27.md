# Public v27 source checkpoint

This branch publishes the source, tests, examples and documentation for 25 runnable chip-rl environments. Its runtime files are byte-identical to local tested checkpoint `91417d22c199a63de74b0ce7798250fc7e368759`. This branch has a new root commit, so local experimental commit history is not reachable from it.

Publication-only changes: evaluation artifacts and the entire `artifacts/` and `evidence/` trees are excluded; links to them in docs are rendered as plain text; the example API checker `scripts/check_requant_api_v26.py` is excluded because it reads a retained private counterexample file; this note and the README publication notice were added. Private vectors, seeds, journals, candidate evaluation runs, netlists, credentials and local archives remain in the local checkpoint and are not published.

The v27 audit demonstrates repairs for specific reset false acceptances in elastic, MSHR and router and preserves the v26 requant repair. The older `f9d7137` checkpoint is historical and predates known judge gaps. This is finite simulation and mapped-synthesis research code, not a proof of general hardware correctness, OS isolation, routed timing, power, or an RL learning gain. Read `docs/reset-audit-v27.md` and `docs/task-inventory.md` for scope and limitations; the raw evidence they describe is retained privately.

Local qualification of the source checkpoint: 190 source tests and 190 installed-wheel tests passed; final affected RTL/mapped, API and replay checks passed. Publication-only documentation changes did not alter `chip_rl/` runtime or tests. These historical local checks are not hosted CI status for this new branch.
