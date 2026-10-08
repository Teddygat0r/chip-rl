# V18 fixed refinement budget

Base60a02f4e5a198c680b6a9c7d701eeb8a2f44ecf9 and prior evidence remain unchanged. Focus only on the K16 shiftadaptive single-output implementation associated with the completed v17 abstract induction.

Try source-bound combinational transition extraction: expose actual DFF Q as symbolic current state and D as next state; reject unsupported sequential cells. Compare original/concrete instrumentation and concrete/abstract transitions under an explicit captured-product state mapping. Substitute equal operands structurally before bit-blasting, rather than increasing the previous nonlinear solver timeout. Independently check reset/capture/hold of the product-snapshot relation and bind every obligation to source/configuration/model hashes and prior case coverage. Record exactly which assumptions come from the established invariant and which remain unproved.

Hard experiment cap:16 SAT commands,20s per solve/35s per command; at most16 preprocessing tool calls (no SAT) and8 HDL linkage simulations. At most20 affected evaluator calls plus44 aggregate calls. Existing90s CPU/3GiB/64MiB file limits and300MiB disk-start guard apply. No solver-budget expansion. If extraction/refinement cannot be completed, retain the exact failed obligation and stop at a reproducible checkpoint. No extra abstract-only campaign.

Preserve previous evidence via verified archives if raw duplicates must be removed. No new tools, credentials, security changes, external uploads, paid services or push. Physical validation remains blocked. Freeze runtime before integration, run source/installed tests and affected/aggregate regressions, and package the strongest justified claim plus the next useful benchmark-development task beyond proof work.
