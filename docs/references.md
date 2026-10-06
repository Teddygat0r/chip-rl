# References and reuse audit

Reviewed on 2026-10-06. All task RTL, Python models, harnesses and workload generators
in this repository are original implementation for this project. No benchmark RTL,
prompts, datasets or third-party testbenches were copied.

- [NVIDIA VerilogEval](https://github.com/NVlabs/verilog-eval): useful reference for
  simulator-driven RTL evaluation and failure categorization. Its
  [license](https://github.com/NVlabs/verilog-eval/blob/main/LICENSE) is MIT and also
  retains an OpenAI human-eval notice. No source/data incorporated.
- [NVIDIA CVDP](https://github.com/NVlabs/cvdp_benchmark): broader design/verification
  benchmark reference. Repository [LICENSE](https://github.com/NVlabs/cvdp_benchmark/blob/main/LICENSE)
  is Apache-2.0. No source/data incorporated; independently audit any future dataset
  imports and per-file notices before reuse.
- [Yosys](https://yosyshq.readthedocs.io/projects/yosys/en/latest/),
  [SBY](https://yosyshq.readthedocs.io/projects/sby/en/latest/) and
  [EQY](https://yosyshq.readthedocs.io/projects/eqy/en/latest/): synthesis, property
  checking and sequential equivalence references. Actual runs here use Yosys SAT;
  SBY and EQY are not installed or claimed as executed.
- [OpenROAD Flow Scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts)
  and [documentation](https://openroad-flow-scripts.readthedocs.io/en/latest/): optional
  physical flow reference. OpenROAD, PDK and standard-cell characterization are not
  installed. Physical validation count is zero.

Runtime tools are externally installed Debian packages: Icarus Verilog 12.0
(GPL-2.0-or-later, with file-specific notices), Yosys 0.52 (ISC and bundled component
notices), and yosys-abc (Berkeley ABC's permissive licenses/notices). The local
bootstrap downloads packages, does not vendor binaries into this repository, and
keeps package copyright files under its local `root/usr/share/doc`. Their license
obligations remain applicable if binaries are redistributed. Package hashes and
tool versions used for qualification are recorded in `artifacts/toolchain.json`.
