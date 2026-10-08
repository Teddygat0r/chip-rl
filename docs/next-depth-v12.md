# Next depth after the memory milestone

MSHR merging and page walking add distinct memory-system behavior, but increasing
the family count is not the most urgent remaining deployment issue. The evaluator
and agent still require a real host trust boundary. Source-only actions prevent
agent-selected commands, budgets and replay settings through the public API; they
do not protect a private judge from an agent given the same host filesystem access.

The useful next work is a separate-process judge deployment with a narrow JSON
transport, evaluator files mounted read-only, private traces and caches absent
from the agent namespace, and supervised process groups. It should demonstrate
that an agent can edit candidate RTL and submit it while attempts to read private
seeds, modify constraints, or survive cancellation fail. Namespace availability
must be tested on the deployment host. Missing isolation must remain explicit;
a permission flag is not proof of confinement.

The v12 process probe already establishes a smaller necessary property: source,
config, seed and partial stdout survive abrupt evaluator death, and a tool timeout
is rejected. It does not provide the isolation layer. The original CRC failure
still cannot be diagnosed without its lost input; keep that separate from these
new process tests and later successful CRC runs.

A second concrete improvement is to package the full public memory protocol into
reset observations. Currently the memory reset includes RTL, a concise constraints
object and evaluation results; training setup must also give the agent
`docs/memory-v12.md`. This is not a hidden constraint, but requiring an external
protocol document makes unattended agent onboarding unnecessarily fragile.

Formal memory safety and physical implementation remain additional work. A
bounded protocol proof should state assumptions on legal response tokens and
reset coordination, and distinguish stability/token conservation from complete
translation semantics or liveness. Physical area/timing would require a working
open PDK and routing flow; present cell counts and workload cycles cannot supply
those claims. No trained policy or end-to-end accelerator performance claim is
part of this checkpoint.
