# Frozen reference holdout qualification

This is a correctness qualification of the 13 already-authored legacy and alternative reference sources from the canonical TRAIN reference panel. It is **not** a model evaluation, policy-training result, architecture search, or evidence of blind model generalization. Keep these DEV/TEST outcomes outside any future model feedback or selection path.

## Result

All 65/65 preregistered DEV/TEST reference attempts passed the pilot runner's finite source and mapped checks. The DEV split passed 24/24 and the TEST split passed 41/41. By family: gather 9/9, MSHR 4/4, sparse24 10/10, block quant 36/36, and Hadamard INT8 6/6. There were no failed attempts or shared-infrastructure stops. Total study wall time was 793.733037 seconds; summed runner-and-spawned-tools CPU time was 777.616069 seconds. No formal or physical qualification was run.

## Freeze and audit trail

Before the first held-out run, each source was regenerated using its family's first TRAIN configuration, checked byte-for-byte against the canonical source SHA-256, and frozen using `frozen_manifest()` in `manifests/`. `registry.json` contains the 13-source roster, exact 65-case plan, canonical TRAIN evidence identity, source and manifest hashes, tool and runner recipe fingerprints, and opaque pairing IDs. Its canonical SHA-256 is `56e1c78c0fcf5e02f09310fcc437455ae755419d7313e5e1a055c749047c60db`.

Each case ran sequentially with the same private random seed for all references at a given family/split/config, a separate benchmark tool prefix, and private artifacts and cache outside the repository. The 65 files in `cases/` retain the raw public `run_case()` result, result hash, manifest identity, and qualification status. `summary.json` contains all denominators and per-family/reference/split counts; its file SHA-256 is `e3761905a7e3d555176623a6c814e3dd8945f11e94727d20872b829859bee41c`. Seeds, vectors, replay records, and tool logs remain private outside the repository.
