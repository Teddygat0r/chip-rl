# Sealed evaluation: owner/candidate boundary

This is a local protocol implementation, not an authenticated service or operating-system sandbox. Candidate-facing requests never select seeds, structures, budgets, objectives, artifact paths or executable commands. The owner must run it on a separate trusted host/container and keep its private directory and evaluator inaccessible to candidates. No such independent host boundary was established in this experiment.

## Lifecycle

1. The evaluator owner chooses supported task slots and a private split, then calls `sealed.create(owner_directory, tasks, split='stress')`. A fresh nonce and private128-bit seeds are stored with the runtime/contract/tool-executable hashes. Only the plan commitment, slot identifiers/tasks and protocol policy go to the candidate owner. Publish or witness the commitment before source submission; a locally editable file alone is not an external witness.
2. The candidate owner freezes every source and supplies ordered `{id, source_sha256}` records. The evaluator owner calls `sealed.register(...)`, producing a submission commitment chained to the plan. No partial batch registration is permitted. Both parties retain the two receipts.
3. The trusted owner starts the JSON-lines CLI below with fixed host arguments. Candidate requests have exactly `{id, rtl}`. Source bytes must match the committed hash. Overrides and unknown fields are rejected. An exclusive attempt record consumes the slot before any evaluator call. A normal process crash/exception consumes it as unproven rather than providing free retries.
4. `sealed.submit` acknowledges only that a slot was recorded, without correctness, reward, detailed metrics, private paths, seeds or diagnostics. Once every slot is attempted, the owner calls `sealed.release(...)`. The release contains batch results, correctness status, rewards and objective eligibility. It can occur once. Incomplete batches cannot release results.
5. Detailed journals remain private. An independent auditor may later inspect them under the agreed disclosure policy. Replays are host-only investigations, not extra candidate submissions. A separate API/worker is needed if repeated untrusted users are to access this interface.

```sh
python -m chip_rl.quality.sealed \
  --root /owner/private/batch \
  --plan-commitment WITNESSED_PLAN_SHA256 \
  --submission-commitment WITNESSED_SOURCES_SHA256 \
  --cache /owner/private/cache
```

Owner lifecycle methods are Python functions in `chip_rl.quality.sealed`; the CLI intentionally exposes only submission. An example full local flow is `scripts/check_sealed.py`, which invokes the installed CLI in child processes and checks valid/bad RTL, source changes, seed/split/path overrides, replay and premature release. Unit tests additionally check changed plan/runtime/tool commitments, evaluator exceptions and duplicate release.

## What the commitments do and do not establish

The plan digest includes a random nonce to prevent guessing a small private-plan space. The runtime digest includes package Python and Markdown; the tool digest covers Yosys, ABC, Icarus and vvp executable contents. It does not bind tool helper binaries/data files, host dynamic libraries, kernel, filesystem permissions or the executor's identity. A witnessed execution-image/package manifest would be needed to bind those dependencies. Fixed expected commitments must arrive through a trusted channel; this module supplies no signatures or authentication.

Exclusive file creation and advisory locking serialize normal local workers, but a malicious owner with filesystem access can rewrite records. This code cannot prevent that owner from forging results, inspecting candidates, or changing both commitments before they are witnessed. It also cannot isolate hostile RTL tools by itself. Existing source checks/resource limits remain useful but are not a security boundary.

Runtime duration, failures to receive a response and final scores remain potential information channels. Batch commitment prevents changing the sources in that batch after feedback; it does not prove that the author never saw fixtures previously or stop adaptation across separately authorized batches. Independent evaluation therefore requires a genuinely separate owner, fresh privately developed fixtures, independently controlled execution/storage, witnessed commitments and a fixed total submission budget. This experiment demonstrates none of that independence and explicitly labels receipts `independence: not established`.
