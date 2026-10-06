# Evaluator boundary

The only agent action is a source string or a whitelisted stage count. It is copied
to a fresh temporary working directory. Agents cannot provide compiler arguments,
testbench code, constraints, paths, shell commands, or baseline metrics through
`ChipEnv.step`. Returned observations/metrics are copies, so editing them cannot
change the baseline. The trusted host generates tests after accepting an action.
No expected outputs or test vectors appear in the candidate source. Every tool
gets CPU/address-space/file-size limits, a sanitized environment, wall timeout and
a separate process group; a timeout kills the entire group.

Candidate source rejects preprocessor/includes, synthesis pragmas (even in comments),
attributes, system calls except signed/unsigned/clog2, delays, strings, initial/final,
force/release and multiple modules. Results require exact scoreboard completion and
replay on synthesized gates. Missing tools and absent proof stages never pass.

This is isolation for constrained RTL actions, **not a hardened multi-tenant service
against HDL compiler exploits**. A local Python caller can modify Python or inspect
published tests because they own the machine. For adversarial training, run the
trusted evaluator under a different OS identity/container with a read-only image,
private test seeds, no network, a writable scratch mount and OS cgroup limits. Give
the agent only the source-action RPC and observations, never a shell or write access
to this checkout. The library does not pretend chmod on a user-owned directory can
hide tests from that same user. Formal and physical tools run only trusted harnesses.

Release artifacts intentionally disclose the reproducible examples. Choose fresh
private heldout seeds on the trusted host for real evaluation; do not train on the
published heldout corpus and then describe it as unseen.

The audit added explicit rejection of testbench hierarchy references and bind/import/
package/program/primitive/config/library/disable constructs. The JSON-lines server
accepts only reset and RTL/stage actions; paths, tool commands, constraints and
baseline values cannot be supplied. This is an API boundary, not privilege separation.
Installed-package tests run outside the checkout. Training failures intentionally
return counterexample snippets. Challenge artifacts include seeds, vectors and error
counterexamples: keep those reports on the trusted host rather than forwarding them
to agents if the challenge set must remain private.

All externally supplied seeds must be exact unsigned 32-bit integers. Numeric
configuration and workload counts are validated before trusted HDL interpolation.
The audit closed a potential testbench-injection path through string seeds; regression
and installed-server tests reject those inputs before a tool executes. This check
belongs to the trusted-input boundary, independently of candidate-source sanitization.
