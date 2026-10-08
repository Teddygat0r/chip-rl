# V23 prospective independent-review-guided audit

Freeze v22 commit191e6c0948501da48affad743fe715f9b0ecbbb5 and its installed wheel. Review guidance is independently authored, but visible to the implementer: this is not a hidden or independently executed evaluation. Run pre-fix checker/parser/HDL probes and report contradictions, overlap and new findings before modifications.

Preserve v22 numerical/resource/ordering/reset contract unless the user explicitly revises it. Reviewer equal-logit acceptance examples conflict with tied-output spread<=1 unit; report full-contract outcomes and isolate arithmetic threshold gates. N in normalization is structural N, all-masked output is exactly zero, reset cancels after one edge, minimum registered latency1, accepted-to-consumed deadline40*N+4 under bounded supplied stalls.448 is a campaign batch limit, not a legal circuit lifetime.

Reference cross-check: separately implemented high-precision Taylor exponential with range reduction and squaring, no Decimal.exp, math.exp or RTL tables. Focus on uncovered mask populations, negative raw differences, representative positions/offsets, transformations and unrounded thresholds. No repeated full65536-pair sweep.

Caps for new work:100 evaluator calls,200 synthesis invocations,2000 HDL simulation invocations; all existing45s HDL/60s synthesis/90s CPU/3GiB process/64MiB tool-file limits retained. Independent numerical comparisons capped at20000 rows across the whole campaign; durable reservation before each audit stage prevents inadvertent repeats. Aggregate43 legacy evaluator calls plus2 layout calls. Maximum four concurrent local evaluation jobs. Pause new batches below300MiB free, retain verified archives before removing duplicates. No new tools/services/installations, paid services, uploads, credentials, security changes or push. No physical or generalized formal claim.

After demonstrated fixes: full exact-final softmax acceptance/mutant matrix, aggregate/API/example/replay, source/installed tests, pinned source/tool hashes and local checkpoint packaging. Continuous-history tests beyond448 may use smallN and additional RTL-only largeN probes to remain within original per-process budgets; report exact stage/configuration coverage without implying allN/allhistories proof. Candidate isolation inspection is read-only and must describe actual permissions and tool behavior, not claim a sandbox.

## Approved continuation, 2026-10-07

Parent explicitly approved cumulative caps of 160 softmax evaluator calls and 4000 HDL simulations, plus one additional 45-call aggregate pass, using existing local resources. The original checkpoint remains preserved. Synthesis (200), numerical audit (20,000 rows), concurrency (4), and per-tool limits remain unchanged. At continuation: 65 completed softmax evaluations, 12 synthesis calls, 1405 simulations. No push, paid provisioning, external upload, credential or security changes are authorized.
