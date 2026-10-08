> Historical v1 evidence; superseded by [v2 remediation](remediation.md).

# GitHub delivery provenance

This compact source snapshot is derived from audited local commit
`a2e7e35000518d8dea447a8ab74bb31cf5eaa0c8`. Implementation, tests, scripts,
examples, package metadata and contract text are byte-for-byte unchanged.
The original two-commit local history is preserved in the cloud executor and
`/workspace/chip-rl.bundle`; this delivery starts a new, compact history so that
omitting generated files actually avoids uploading those files in ancestor commits.

Included evidence: audit and original qualification summaries, per-case result JSON,
unit-test transcripts, installed-agent rollout results, tool provenance and source
hashes. Excluded: generated netlists, simulation binaries, bulk vectors, duplicated
RTL/testbenches, synthesis/formal logs, wheels/build trees, tool binaries and local
bundles. No credentials or private keys were found by the scoped pattern/filename
scan; this is not a guarantee of absence of every possible secret.

`docs/audit.md` describes final measurements; `docs/validation.md` records historical
qualification. References there to raw artifacts and cloud executor paths describe
the full local bundle, not additional files hosted in this compact GitHub snapshot.
Run `python -m chip_rl.suite --output /tmp/chip-rl-release` to regenerate full evidence.

The audited tree contained no GitHub Actions workflow. This delivery adds no workflow;
local test evidence must not be represented as a green GitHub CI run.
