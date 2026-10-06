# Trust boundary

The agent submits complete RTL source text through `ChipEnv.step` or the JSON-lines
server. It cannot set evaluator seeds, constraints, artifacts, commands, baselines,
or resource limits. Observations contain public contracts, source and coarse
qualification outcomes/aggregate metrics. Raw errors, vectors, simulator logs and
replay seeds are not observations. Workloads change on every action using OS entropy;
`reset(seed)` does not seed evaluation. Trusted-host replay flags are deliberately
separate from the agent interface.

Source screening rejects file I/O, system tasks, preprocessor directives, attributes,
hierarchical testbench access, extra modules, delays and unsupported elaboration.
Mapped netlists are checked for interface, cell/depth budgets, positive-edge clock
identity and absence of latches/asynchronous reset. RTL and mapped simulation must
agree; deadlines, noncompletion and timeouts fail closed. Screening is defense in
depth, not a security proof. Resource limits are 90s CPU, 120s synthesis wall time,
30s simulation wall time, 3GiB address space and 64MiB output files per process.

Temporary working directories are private and tool subprocesses receive a minimal
environment. Trusted caches are mode 0700 and keyed by source, configuration,
contract and tool executable hashes; private baseline memoization additionally
includes workload/recipe identity. Cached baseline records retain replay metadata.
A host that gives the candidate the same user account or filesystem permissions
can invalidate these guarantees. Python objects are not protected from arbitrary
Python code executed in the same process.

A real `bwrap` user/PID/network isolation probe failed in this executor with
`setting up uid map: Read-only file system`. Therefore `os_isolation` is always
`not_provided`. No hard compiler sandbox is claimed. For untrusted autonomous
agents, put the evaluator behind a separately administered container/VM and permit
only source-only requests. Private artifacts must not enter the agent workspace.
