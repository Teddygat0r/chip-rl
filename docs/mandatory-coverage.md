# Mandatory coverage correction (0.3.0)

The v2 release suite rejected late-drop mutants using longer streams, while the
ordinary API used only 53 dot/tensor commands. Reporting checks confirmed that the
same 64-command-cutoff mutants passed the default API. Private seeds did not repair
this coverage omission. Historical v2 counts describe those executed profiles only.

`chip_rl.coverage.cases` now creates the required plan for every qualification:

- Two target-configuration cases, with random workload-unit counts drawn from
  128..256 and 1024..1280.
- One case per other supported structural dimension, drawn from 512..768.
- All existing directed reset/cold-read, cache alias, signed-extreme, arbitration,
  compaction, stall, completion and resource checks in each relevant case.
- Unchanged candidate source under all relevant WIDTH/DEPTH/K overrides.

Workload units expand into task-specific commands and directed prefixes. These
bands are public; the chosen lengths, operands and schedules are private. Legacy
trusted-host `count` requests can increase the floors, never reduce them. The suite
and heldout scripts no longer specify a stronger count than ordinary evaluation.
The default CLI, direct library, ChipEnv and JSON reset/step all call this same gate.
The optional physical launcher's functional prerequisite also uses it.

Cheap RTL preflight can reject an invalid candidate before paired baseline work,
but cannot qualify it. Success still requires synthesis, mapped-netlist simulation,
all mandatory cases, budgets, and paired baseline scoring. Single-case replay now
reports `case_replay_passed` and explicitly says qualification was not performed.
It is a diagnostic tool, not an alternate qualification path.

Other intentionally different host controls are deterministic replay seeds, cache
and artifact paths, larger workload floors, explicit Config overrides and an opt-in
for excluded experimental families. They are unavailable in JSON agent actions.
Caches change execution cost, not required coverage. Different fresh private samples
can naturally change scores or expose failures; API equivalence means common
acceptance rules, not identical metrics across independent random draws.

Every case has at most `min(max_cycles, 32*commands+128)` simulated clocks, normally
30,000. The larger gather workload exposed a 30-second wall timeout, which correctly
rejected the candidate. The shared simulation wall budget was explicitly increased
to 120 seconds, retaining the 90-second CPU, 3GiB address-space and 64MiB output-file
limits. There is no timeout fallback, shorter-profile retry or timeout-as-pass rule.
The original timeout and subsequent retest are retained as separate evidence.

The API regression script runs the actual installed JSON process, CLI subprocesses,
and direct library calls with default evaluation arguments. It covers every existing
family-specific attack class and adds dot/tensor cutoffs 127, 257, 777 and 1023,
in addition to 64. Valid baselines are positive controls. Fixed winners are then
checked on fresh private mandatory profiles, without choosing source after seeing
those samples. Full counts and results are recorded in `evidence/v3` after completion.

Finite streams cannot prove an unbounded transaction contract. A later cutoff beyond
all sampled lengths can still evade these tests. This correction closes the known
profile mismatch; it is not a claim of universal exploit resistance, independent
out-of-distribution evaluation, trained RL, physical PPA or silicon readiness.
The six pilot families and four excluded experimental models are unchanged. An
external OS trust boundary remains necessary: this executor provides no hard
compiler/agent sandbox. Formal evidence remains bounded; physical validation is zero.
