# Reproduce the N=4 fixed-footprint comparison

Install or extract the following official releases into local, separate tool prefixes: ORFS revision `87b01b74b92d6e77edcdbe86949ee7eb6017ac7d`; OpenROAD `26Q2-1164-g08f67ee5ec` Ubuntu 24.04 package (SHA256 `f3f1eeaa18f327503f72cc45dcef5b1514ec2e89726ec53b4553bf4f951168a3`); YosysHQ OSS CAD Suite `2026-10-08` linux-x64 archive (SHA256 `8fa59d93d6cadbbee352077c059f2c5b72cda301e4508d9064a23d1ec11579c7`); Debian KLayout `0.30.0-1+b1` package (SHA256 `421e473f7a1e0e4aa6b20dd1ca69b494c21e38308c38ad9259a7476cf4c3f272`) and matching Debian Ruby 3.3/Qt XML Patterns runtime libraries. ORFS tarball SHA256 is `df2b06ac766d9d32a77fc35e79588cab18e66d38e41c8c345bdcec7e1c1934fd`. Do not mix these with a newer ORFS master, which required an OpenROAD command absent in this pin.

The public `serial.mk` and `serial_comb_root.mk` are portable path-rebased equivalents of the original frozen Makefiles. All physical parameters are in the unchanged `config/common.mk` and `config/constraints.sdc`. The original location-specific hashes remain in `as_run_hashes.sha256`.

From this bundle's directory, set absolute paths to `ORFS_FLOW` (the pinned ORFS `flow` directory), `OPENROAD_EXE`, `YOSYS_EXE`, and `KLAYOUT_CMD`. On Debian 13, the extracted OpenROAD package needs `LD_LIBRARY_PATH` set to its extracted `/opt/or-tools/lib` and `/usr/lib/x86_64-linux-gnu`; KLayout needs the extracted `/usr/lib/klayout` and `/usr/lib/x86_64-linux-gnu` paths and `RUBYLIB` set to the extracted Ruby `/usr/lib/ruby/3.3.0` and `/usr/lib/x86_64-linux-gnu/ruby/3.3.0`. These paths are tool installation locations, not design parameters.

Run the two designs sequentially, with two OpenROAD threads and a 3 GB virtual-address-space limit per process:

```
for variant in serial serial_comb_root; do
  (
    cd "$ORFS_FLOW"
    ulimit -v 3145728
    make -j1 DESIGN_CONFIG="$BUNDLE/config/$variant.mk" \
      WORK_HOME="$BUNDLE/runs/$variant" FLOW_VARIANT=base \
      OPENROAD_EXE="$OPENROAD_EXE" YOSYS_EXE="$YOSYS_EXE" \
      KLAYOUT_CMD="$KLAYOUT_CMD" all gds
  )
done
```

Set `BUNDLE` to this bundle's absolute path first. The pre-route testbench and 39 canonical expected 64-bit vectors are in `smoke/`. Run them against each source wrapper and Nangate45 mapped netlist; the given vectors include blocking-output stability. ORFS reference-deck DRC can be invoked via `make ... drc` with a separate 30-minute wall cap per design, but both original capped runs were CPU-active and incomplete in the deck's ACTIVE.1 Euclidean-width check. An incomplete DRC is not a DRC pass. No post-route functional equivalence, SDF simulation, LVS, or foundry signoff was performed.
