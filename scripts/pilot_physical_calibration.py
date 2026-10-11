"""Freeze and run the ten authored TRAIN-only Nangate45 reference cases.

Freeze is deliberately separate from measurement.  No result-dependent retry or
constraint tuning is supported.  Work directories (including private vectors and
raw logs) must be outside the repository; only compact redacted results are public.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
from queue import Empty
import re
import resource
import secrets
import shutil
import signal
import subprocess
import sys
import time
import traceback

import psutil

REPO = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = REPO / "evidence/pilot-physical-calibration"
SCRIPT = Path(__file__).resolve()
CASES = (
    ("gather", 16, "legacy_baseline"), ("gather", 16, "static_decoded"),
    ("mshr", 2, "ring"), ("mshr", 2, "shift"),
    ("sparse24", 2, "serial"), ("sparse24", 2, "pipeline"),
    ("block_quant", 4, "serial"), ("block_quant", 4, "chunked4"),
    ("hadamard_int8", 4, "serial_butterfly"),
    ("hadamard_int8", 4, "sized_serial_butterfly"),
)
PARAMETER = {"gather": "DEPTH", "mshr": "ENTRIES", "sparse24": "G",
             "block_quant": "N", "hadamard_int8": "N"}
PROCESS_VM_KIB = 3 * 1024 * 1024
CASE_WALL_S = 600
FLOW_ROOT = REPO.parent / "physical-tools/orfs/flow"
TOOLS_ROOT = REPO.parent / "physical-tools"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(data: str | bytes) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def source_for(family: str, parameter: int, label: str) -> str:
    if (family, parameter, label) not in CASES:
        raise ValueError("case is outside the ten fixed TRAIN cases")
    if family == "gather":
        from chip_rl.tasks import Config
        if label == "legacy_baseline":
            from chip_rl.rtl import design
        else:
            from chip_rl.gather_reference import design
        # Original source bytes are identical across parameterizations; the
        # physical wrapper, rather than the default declaration, overrides DEPTH.
        return design(Config("gather"))
    if family == "mshr":
        from chip_rl.memory.spec import Config
        from chip_rl.memory.rtl import design
        return design(Config("mshr"), label)
    if family == "sparse24":
        from chip_rl.sparse24.rtl import design
    elif family == "block_quant":
        from chip_rl.block_quant.rtl import design
    else:
        from chip_rl.hadamard_int8.rtl import design
    return design(label)


def case_id(family: str, parameter: int, label: str) -> str:
    return f"{family}-{PARAMETER[family]}{parameter}-{label}"


def _mshr_ports() -> dict:
    from chip_rl.memory.spec import PORTS
    return PORTS


def _stream_ports(input_width: int, output_width: int) -> dict:
    return {"clk": ("input", 1), "rst": ("input", 1),
            "in_valid": ("input", 1), "in_ready": ("output", 1),
            "in_data": ("input", input_width), "out_valid": ("output", 1),
            "out_ready": ("input", 1), "out_data": ("output", output_width)}


def _port_list(ports: dict) -> str:
    return ",\n  ".join(f"{direction} " + (f"[{width-1}:0] " if width > 1 else "") + name
                          for name, (direction, width) in ports.items())


def wrapper(family: str, parameter: int) -> str:
    """Physical top; constant-fill precisely the inactive input and output bits."""
    if family == "mshr":
        ports = _mshr_ports()
        wires = ", ".join(f".{name}({name})" for name in ports)
        return (f"module physical_top(\n  {_port_list(ports)}\n);\n"
                f"candidate #(.ENTRIES({parameter})) core ({wires});\nendmodule\n")
    widths = {"gather": (48, 136), "sparse24": (174, 32),
              "block_quant": (64, 36), "hadamard_int8": (32, 64)}
    iw, ow = widths[family]
    ports = _stream_ports(iw, ow)
    full_input = {
        "gather": "{464'b0,in_data}",
        "sparse24": "{2'b0,in_data[173:112],336'b0,in_data[111:0]}",
        "block_quant": "{448'b0,in_data}",
        "hadamard_int8": "{480'b0,in_data}",
    }[family]
    full_output_width = 32 if family == "sparse24" else 256
    output = {"gather": "full_out[135:0]", "sparse24": "full_out",
              "block_quant": "{full_out[131:128],full_out[31:0]}",
              "hadamard_int8": "full_out[63:0]"}[family]
    return (f"module physical_top(\n  {_port_list(ports)}\n);\n"
            f"wire [{full_output_width-1}:0] full_out;\n"
            f"candidate #(.{PARAMETER[family]}({parameter})) core ("
            ".clk(clk),.rst(rst),.in_valid(in_valid),.in_ready(in_ready),"
            f".in_data({full_input}),.out_valid(out_valid),.out_ready(out_ready),"
            ".out_data(full_out));\n"
            f"assign out_data = {output};\nendmodule\n")


def mapped_candidate_adapter(family: str) -> str:
    """Restore the exact original full interface for the official simulators."""
    if family == "mshr":
        ports = _mshr_ports()
        wires = ", ".join(f".{name}({name})" for name in ports)
        return f"module candidate(\n  {_port_list(ports)}\n);\nphysical_top dut ({wires});\nendmodule\n"
    from chip_rl.sparse24.spec import PORTS as SPARSE_PORTS
    from chip_rl.block_quant.spec import PORTS as FULL_PORTS
    ports = SPARSE_PORTS if family == "sparse24" else FULL_PORTS
    clipped_input = {"gather": "in_data[47:0]", "sparse24":
                     "{in_data[509:448],in_data[111:0]}",
                     "block_quant": "in_data[63:0]", "hadamard_int8": "in_data[31:0]"}[family]
    output = {"gather": "{120'b0,compact_out}", "sparse24": "compact_out",
              "block_quant": "{124'b0,compact_out[35:32],96'b0,compact_out[31:0]}",
              "hadamard_int8": "{192'b0,compact_out}"}[family]
    ow = {"gather": 136, "sparse24": 32, "block_quant": 36, "hadamard_int8": 64}[family]
    return (f"module candidate(\n  {_port_list(ports)}\n);\n"
            f"wire [{ow-1}:0] compact_out;\n"
            "physical_top dut (.clk(clk),.rst(rst),.in_valid(in_valid),"
            f".in_ready(in_ready),.in_data({clipped_input}),.out_valid(out_valid),"
            ".out_ready(out_ready),.out_data(compact_out));\n"
            f"assign out_data = {output};\nendmodule\n")


def constraints() -> str:
    return ("current_design physical_top\n"
            "create_clock -name clk -period 20 [get_ports clk]\n"
            "set_input_delay 4 -clock clk [all_inputs -no_clocks]\n"
            "set_output_delay 4 -clock clk [all_outputs]\n")


def config() -> str:
    return ("export DESIGN_NAME = physical_top\nexport PLATFORM = nangate45\n"
            "export VERILOG_FILES = $(abspath $(dir $(DESIGN_CONFIG))/source.v) "
            "$(abspath $(dir $(DESIGN_CONFIG))/wrapper.v)\n"
            "export SDC_FILE = $(abspath $(dir $(DESIGN_CONFIG))/constraints.sdc)\n"
            "export DIE_AREA = 0 0 140 140\nexport CORE_AREA = 10 10 130 130\n"
            "export PLACE_DENSITY = 0.55\nexport NUM_CORES = 2\n"
            "export SYNTH_REPEATABLE_BUILD = 1\n")


def _tool_paths() -> dict[str, Path]:
    paths = {"openroad": TOOLS_ROOT / "openroad/usr/bin/openroad",
             "yosys": TOOLS_ROOT / "oss-cad-suite/bin/yosys",
             "iverilog": TOOLS_ROOT / "oss-cad-suite/bin/iverilog",
             "vvp": TOOLS_ROOT / "oss-cad-suite/bin/vvp"}
    if any(not p.is_file() for p in paths.values()):
        raise FileNotFoundError("a pinned physical or simulator executable is missing")
    return paths


def _flow_inputs() -> dict[str, Path]:
    platform = FLOW_ROOT / "platforms/nangate45"
    entries = {"makefile": FLOW_ROOT / "Makefile",
               "liberty": platform / "lib/NangateOpenCellLibrary_typical.lib",
               "tech_lef": platform / "lef/NangateOpenCellLibrary.tech.lef",
               "macro_lef": platform / "lef/NangateOpenCellLibrary.macro.mod.lef",
               "rcx_rules": platform / "rcx_patterns.rules",
               "platform_config": platform / "config.mk",
               "cells_adders": platform / "cells_adders.v",
               "cells_latch": platform / "cells_latch.v",
               "cells_clkgate": platform / "cells_clkgate.v"}
    entries.update({"flow_script/" + str(p.relative_to(FLOW_ROOT / "scripts")): p
                    for p in sorted((FLOW_ROOT / "scripts").rglob("*")) if p.is_file()})
    if any(not p.is_file() for p in entries.values()):
        raise FileNotFoundError("a pinned ORFS flow input is missing")
    return entries


def _manifest_payload(root: Path) -> dict:
    if not (FLOW_ROOT / "Makefile").is_file():
        raise FileNotFoundError("pinned ORFS flow is unavailable")
    tools = _tool_paths()
    flow = _flow_inputs()
    rows = []
    for family, parameter, label in CASES:
        name = case_id(family, parameter, label)
        case = root / "cases" / name
        rows.append({"case": name, "family": family, "parameter_name": PARAMETER[family],
                     "parameter": parameter, "reference": label, "split": "train",
                     "source_sha256": sha(case / "source.v"),
                     "wrapper_sha256": sha(case / "wrapper.v"),
                     "constraints_sha256": sha(case / "constraints.sdc"),
                     "config_sha256": sha(case / "config.mk")})
    return {"schema": "pilot-physical-calibration-v1", "cases": rows,
            "physical_protocol": {"platform": "nangate45", "die_um": [0, 0, 140, 140],
                                  "core_um": [10, 10, 130, 130],
                                  "requested_place_density": 0.55, "clock_ns": 20,
                                  "input_delay_ns": 4, "output_delay_ns": 4,
                                  "reset_timed": True, "threads": 2,
                                  "sequential_cases": True, "process_vm_kib": PROCESS_VM_KIB,
                                  "case_wall_seconds": CASE_WALL_S,
                                  "targets": ["synth", "route", "do-finish"],
                                  "gds": False, "klayout": False, "reference_deck_drc": False},
            "tool_sha256": {k: sha(v) for k, v in tools.items()},
            "flow_input_sha256": {k: sha(v) for k, v in flow.items()},
            "runner_sha256": sha(SCRIPT)}


def freeze(root: Path = DEFAULT_EVIDENCE) -> dict:
    root = root.resolve()
    if root.exists():
        raise FileExistsError("freeze directory already exists; no overwrite or re-freeze")
    # Resolve and hash all external inputs before creating a partial freeze.
    _tool_paths(); _flow_inputs()
    root.mkdir(parents=True)
    for family, parameter, label in CASES:
        case = root / "cases" / case_id(family, parameter, label)
        case.mkdir(parents=True)
        (case / "source.v").write_text(source_for(family, parameter, label))
        (case / "wrapper.v").write_text(wrapper(family, parameter))
        (case / "constraints.sdc").write_text(constraints())
        (case / "config.mk").write_text(config())
    payload = _manifest_payload(root)
    payload["freeze_sha256"] = digest(canonical(payload))
    (root / "manifest.json").write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    return payload


def verify_freeze(root: Path) -> dict:
    root = root.resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    token = manifest.pop("freeze_sha256")
    if digest(canonical(manifest)) != token:
        raise ValueError("frozen manifest was modified")
    fresh = _manifest_payload(root)
    if fresh != manifest:
        raise ValueError("frozen source, wrapper, constraints, recipe or tool hash changed")
    for row in manifest["cases"]:
        family, parameter, label = row["family"], row["parameter"], row["reference"]
        case = root / "cases" / row["case"]
        if (case / "source.v").read_text() != source_for(family, parameter, label):
            raise ValueError("original source changed")
        if (case / "wrapper.v").read_text() != wrapper(family, parameter):
            raise ValueError("wrapper changed")
        if (case / "constraints.sdc").read_text() != constraints() or (case / "config.mk").read_text() != config():
            raise ValueError("physical constraint changed")
    manifest["freeze_sha256"] = token
    return manifest


def _nangate_models(private_root: Path, manifest: dict) -> Path:
    """Create functional Verilog directly from the frozen official Nangate Liberty."""
    lib = _flow_inputs()["liberty"]
    model = private_root / "nangate_models.v"
    cmd = [str(_tool_paths()["yosys"]), "-Q", "-T", "-p",
           f"read_liberty -ignore_miss_func {lib}; write_verilog -noattr {model}"]
    with (private_root / "liberty_conversion.log").open("w") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True, preexec_fn=_limits)
        try:
            proc.wait(timeout=45)
        except subprocess.TimeoutExpired as exc:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise TimeoutError("Nangate cell-model conversion timed out") from exc
        if proc.returncode:
            raise RuntimeError("Nangate cell-model conversion failed; private log retained")
    if not model.is_file() or "module DFF_X1" not in model.read_text():
        raise RuntimeError("Nangate functional cell-model generation failed")
    return model


def _mapped_full_netlist(case_row: dict, mapped: Path, models: Path, private_root: Path) -> Path:
    netlist = private_root / "mapped_candidate.v"
    netlist.write_text(mapped.read_text() + "\n" + mapped_candidate_adapter(case_row["family"])
                       + "\n" + models.read_text())
    return netlist


def finite_check(row: dict, source: str, mapped: Path, models: Path, work: Path,
                 seed: int) -> dict:
    """Use the existing exact/protocol harnesses at the single TRAIN parameter."""
    family, n = row["family"], row["parameter"]
    # Existing trusted simulators use `tool()` and inherit this local process
    # PATH.  Do not install into or edit the separate benchmark toolchain.
    os.environ["PATH"] = str(TOOLS_ROOT / "oss-cad-suite/bin") + os.pathsep + os.environ["PATH"]
    work.mkdir(parents=True, exist_ok=False)
    full_netlist = _mapped_full_netlist(row, mapped, models, work)
    # The seed is random, stored in the private work root, and paired across
    # the baseline and alternative within a family/configuration.
    if family == "gather":
        from chip_rl.tasks import Config
        from chip_rl.evaluate import TrustedEvaluator
        cache = work / "private-cache"
        cache.mkdir()
        host = TrustedEvaluator(cache)
        fake_build = work / "mapped-build"
        fake_build.mkdir()
        shutil.copy(full_netlist, fake_build / "netlist.v")
        replays = []
        for band, count in (("target_short", 128), ("target_long", 1024)):
            sim = host._simulate(Config("gather", depth=n), source, fake_build,
                                 seed + (0 if band == "target_short" else 1), count,
                                 work / ("private-" + band))
            if sim["commands"] <= 0 or sim["cycles"] <= 0:
                raise RuntimeError("incomplete gather official replay")
            replays.append({"band": band, "commands": sim["commands"]})
        if len(replays) != 2:
            raise RuntimeError("incomplete gather official replay")
        return {"official_simulator": "gather.TrustedEvaluator._simulate", "replays": replays}
    if family == "mshr":
        from chip_rl.memory.spec import Config
        from chip_rl.memory import workloads, simulation
        c = Config("mshr", entries=n)
        workload = workloads.generate(c, seed, heldout=False)
        result = simulation.simulate(c, source, full_netlist, workload, work / "private-simulation")
        if not result.get("vectors_sha256"):
            raise RuntimeError("incomplete MSHR official replay")
        return {"official_simulator": "memory.simulation.simulate", "passed": True}
    if family == "sparse24":
        from chip_rl.sparse24 import decoder_check, simulation, workloads
        workload = workloads.generate(n, seed, "development")
        decoder_check.check(n, source, full_netlist, work / "private-decoder")
        result = simulation.simulate(n, source, full_netlist, workload, work / "private-simulation")
        if not result.get("rtl_mapped_checked"):
            raise RuntimeError("incomplete sparse24 official replay")
        return {"official_simulator": "sparse24.decoder_check+simulation", "passed": True}
    if family == "block_quant":
        from chip_rl.block_quant import arithmetic_check, simulation, workloads
        workload = workloads.generate(n, seed, "development")
        arithmetic_check.check(n, source, full_netlist, workload, work / "private-arithmetic")
        result = simulation.simulate(n, source, full_netlist, workload, work / "private-simulation")
        if not result.get("rtl_mapped_checked"):
            raise RuntimeError("incomplete block-quant official replay")
        return {"official_simulator": "block_quant.arithmetic_check+simulation", "passed": True}
    from chip_rl.hadamard_int8 import exact_check, simulation, workloads
    workload = workloads.generate(n, seed, "development")
    exact_check.check(n, source, full_netlist, workload, work / "private-exact")
    result = simulation.simulate(n, source, full_netlist, workload, work / "private-simulation")
    if not result.get("rtl_mapped_checked"):
        raise RuntimeError("incomplete Hadamard official replay")
    return {"official_simulator": "hadamard_int8.exact_check+simulation", "passed": True}


def _limits() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (PROCESS_VM_KIB * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _make(target: str, case_dir: Path, run_root: Path, log: Path, deadline: float) -> dict:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("ten-minute case wall cap reached")
    tools = _tool_paths()
    env = os.environ.copy()
    env["PATH"] = str(TOOLS_ROOT / "oss-cad-suite/bin") + os.pathsep + env.get("PATH", "")
    setup = TOOLS_ROOT / "env.sh"
    if setup.exists():
        # The restored tool prefix is local and does not modify the benchmark toolchain.
        env["LD_LIBRARY_PATH"] = ":".join((str(TOOLS_ROOT / "openroad/opt/or-tools/lib"),
            str(TOOLS_ROOT / "openroad/usr/lib/x86_64-linux-gnu"),
            str(TOOLS_ROOT / "openroad-deps/usr/lib/x86_64-linux-gnu"),
            env.get("LD_LIBRARY_PATH", "")))
    cmd = ["make", "-j1", "-C", str(FLOW_ROOT), "DESIGN_CONFIG=" + str(case_dir / "config.mk"),
           "WORK_HOME=" + str(run_root), "FLOW_VARIANT=base",
           "OPENROAD_EXE=" + str(tools["openroad"]), "YOSYS_EXE=" + str(tools["yosys"]), target]
    started = time.monotonic()
    peak_rss_kib = None
    with log.open("w") as stream:
        proc = subprocess.Popen(cmd, stdout=stream, stderr=subprocess.STDOUT, env=env,
                                start_new_session=True, preexec_fn=_limits)
        while proc.poll() is None:
            if time.monotonic() >= deadline:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                raise TimeoutError(f"{target} exceeded ten-minute case wall cap")
            try:
                process = psutil.Process(proc.pid)
                processes = [process] + process.children(recursive=True)
                rss = sum(p.memory_info().rss for p in processes if p.is_running()) // 1024
                peak_rss_kib = max(rss, peak_rss_kib or 0)
            except (psutil.Error, ProcessLookupError):
                pass
            time.sleep(0.2)
        proc.wait()
    if proc.returncode:
        raise RuntimeError(f"{target} failed with exit {proc.returncode}; private log retained")
    return {"elapsed_s": round(time.monotonic() - started, 3),
            "peak_rss_kib": peak_rss_kib, "exit_code": proc.returncode}


def _number(data: dict, key: str):
    value = data.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value if math.isfinite(value) else None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _stage_json(run_root: Path, name: str) -> dict:
    files = list(run_root.rglob(name))
    if len(files) != 1:
        return {}
    try:
        return json.loads(files[0].read_text())
    except (OSError, ValueError):
        return {}


def _report_delay(run_root: Path):
    reports = list(run_root.rglob("6_finish.rpt"))
    if len(reports) != 1:
        return None
    match = re.search(r"(?m)^finish critical path delay\s*\n[-]+\s*\n\s*([-+]?\d+(?:\.\d+)?)",
                      reports[0].read_text())
    return float(match.group(1)) if match else None


def _stage_resource(log: Path) -> dict:
    if not log.exists():
        return {"elapsed_s": None, "cpu_s": None, "peak_rss_kib": None}
    data = log.read_text(errors="replace")
    elapsed = re.findall(r"Elapsed time:\s*([0-9:.]+)\[h:\]min:sec", data)
    elapsed_s = None
    if elapsed:
        parts = elapsed[-1].split(":")
        if len(parts) in (2, 3):
            try:
                values = [float(part) for part in parts]
                elapsed_s = sum(value * 60 ** exponent for exponent, value in
                                enumerate(reversed(values)))
                if not math.isfinite(elapsed_s):
                    elapsed_s = None
            except ValueError:
                pass
    cpu = re.findall(r"CPU time:\s*user\s+([0-9.]+)\s+sys\s+([0-9.]+)", data)
    cpu_s = sum(map(float, cpu[-1])) if cpu else None
    if cpu_s is not None and not math.isfinite(cpu_s):
        cpu_s = None
    rss = re.findall(r"Peak memory:\s*([0-9]+)KB", data)
    return {"elapsed_s": elapsed_s, "cpu_s": cpu_s,
            "peak_rss_kib": int(rss[-1]) if rss else None}


def _actual_place_density(run_root: Path, metrics: dict):
    # The requested target and actual implementation utilization are separate.
    for key in ("globalplace__density__target", "globalplace__place__density"):
        value = _number(metrics, key)
        if value is not None:
            return value
    logs = list(run_root.rglob("3_3_place_gp.log"))
    if len(logs) != 1:
        return None
    text = logs[0].read_text(errors="replace")
    for pattern in (r"Placement density is\s+([0-9.]+)",
                    r"initial placement density(?: is|:)\s+([0-9.]+)",
                    r"target density(?: is|:)\s+([0-9.]+)"):
        match = re.search(pattern, text, re.I)
        if match:
            value = float(match.group(1))
            if math.isfinite(value):
                return value
    return None


def extract_metrics(run_root: Path) -> dict:
    synth = _stage_json(run_root, "1_2_yosys_metrics.json")
    route = _stage_json(run_root, "5_2_route.json")
    finish = _stage_json(run_root, "6_report.json")
    floor = _stage_json(run_root, "2_1_floorplan.json")
    place = _stage_json(run_root, "3_3_place_gp.json")
    all_json = synth | floor | place | route | finish
    logs = list(run_root.rglob("5_2_route.log"))
    detail_resource = _stage_resource(logs[0]) if len(logs) == 1 else _stage_resource(Path("/nonexistent"))
    result = {
        "mapped_stdcell_area_um2": _number(all_json, "synth__design__instance__area__stdcell"),
        "physical_stdcell_area_um2": _number(all_json, "finish__design__instance__area"),
        "setup_slack_ns": _number(all_json, "finish__timing__setup__ws"),
        "setup_tns_ns": _number(all_json, "finish__timing__setup__tns"),
        "hold_slack_ns": _number(all_json, "finish__timing__hold__ws"),
        "hold_tns_ns": _number(all_json, "finish__timing__hold__tns"),
        "reported_path_delay_ns": _report_delay(run_root),
        "route_violation_count": _number(all_json, "detailedroute__route__drc_errors"),
        "route_wirelength_um": _number(all_json, "detailedroute__route__wirelength"),
        "antenna_violating_nets": _number(all_json, "detailedroute__antenna__violating__nets"),
        "requested_place_density": 0.55,
        "effective_place_density": _actual_place_density(run_root, all_json),
        "floorplan_die_um": [0, 0, 140, 140], "floorplan_core_um": [10, 10, 130, 130],
        "actual_die_area_um2": _number(all_json, "floorplan__design__die__area"),
        "actual_core_area_um2": _number(all_json, "floorplan__design__core__area"),
        "actual_cell_utilization": _number(all_json, "finish__design__instance__utilization"),
        "detail_route_resources": detail_resource,
        "rc_extraction": "OpenRCX extracted SPEF" if list(run_root.rglob("6_final.spef")) else "unverified",
    }
    return result


def _run_dir(private_root: Path, name: str) -> Path:
    path = private_root / name
    path.mkdir(parents=True, exist_ok=False)
    return path


def _empty_record(row: dict, manifest: dict, seed_id: str) -> dict:
    return {"case": row["case"], "family": row["family"], "config": row["parameter"],
            "reference_name": row["reference"], "is_baseline": row["reference"] in
            ("legacy_baseline", "ring", "serial", "serial_butterfly"),
            "source_sha256": row["source_sha256"], "freeze_sha256": manifest["freeze_sha256"],
            "seed_id": seed_id, "generic_cells": None,
            "physical_stdcell_area_um2": None, "setup_slack_ns": None,
            "route_violation_count": None, "physical_stage": "not_started",
            "finite_pre_route_checked": False, "route_completed": False,
            "metrics": None, "error": None, "elapsed_s": None,
            "cpu_s": None, "peak_rss_kib": None, "stage_resources": {},
            "formal_equivalence": "not_run", "post_route_functional": "not_run",
            "signoff": False}


def _measure_one(row: dict, root: Path, work: Path, models: Path, manifest: dict,
                 seed: int, seed_id: str, answer: multiprocessing.Queue) -> None:
    """Isolated case worker so the parent can enforce the entire wall cap."""
    os.setsid()
    _limits()
    case_dir = root / "cases" / row["case"]
    run_root = work / "orfs"
    began = time.monotonic()
    cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    deadline = began + CASE_WALL_S
    record = _empty_record(row, manifest, seed_id)
    try:
        record["physical_stage"] = "synthesis"
        record["stage_resources"]["synth"] = _make("synth", case_dir, run_root,
                                                       work / "synth_make.log", deadline)
        mapped_paths = list(run_root.rglob("1_2_yosys.v"))
        if len(mapped_paths) != 1:
            raise RuntimeError("expected exactly one mapped ORFS synthesis netlist")
        record["physical_stage"] = "finite_pre_route"
        checked = finite_check(row, (case_dir / "source.v").read_text(), mapped_paths[0],
                               models, work / "functional", seed)
        record["finite_pre_route_checked"] = True
        record["functional_check"] = checked
        record["physical_stage"] = "pre_route_functional_pass"
        record["stage_resources"]["route"] = _make("route", case_dir, run_root,
                                                       work / "route_make.log", deadline)
        if not list(run_root.rglob("5_route.odb")) or not list(run_root.rglob("5_route.sdc")):
            raise RuntimeError("detailed route outputs missing")
        record["route_completed"] = True
        record["physical_stage"] = "detailed_route"
        record["stage_resources"]["report"] = _make("do-finish", case_dir, run_root,
                                                        work / "report_make.log", deadline)
        record["physical_stage"] = "post_route_report"
    except Exception as exc:
        (work / "private-error.txt").write_text(traceback.format_exc())
        record["error"] = type(exc).__name__ + " at " + record["physical_stage"]
    finally:
        record["elapsed_s"] = round(time.monotonic() - began, 3)
        cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        record["cpu_s"] = round(cpu_after.ru_utime + cpu_after.ru_stime
                                - cpu_before.ru_utime - cpu_before.ru_stime, 3)
        rss_values = [r["peak_rss_kib"] for r in record["stage_resources"].values()
                      if r["peak_rss_kib"] is not None]
        record["peak_rss_kib"] = max(rss_values) if rss_values else None
        record["metrics"] = extract_metrics(run_root) if run_root.exists() else None
        if record["metrics"] is not None:
            record["physical_stdcell_area_um2"] = record["metrics"]["physical_stdcell_area_um2"]
            record["setup_slack_ns"] = record["metrics"]["setup_slack_ns"]
            record["route_violation_count"] = record["metrics"]["route_violation_count"]
        answer.put(record)


def _kill_case_tree(process: multiprocessing.Process) -> None:
    """Kill the isolated case plus its simulator/ORFS process groups on timeout."""
    if process.pid is None:
        return
    try:
        parent = psutil.Process(process.pid)
        descendants = parent.children(recursive=True)
    except psutil.Error:
        descendants = []
    groups = set()
    for pid in [p.pid for p in descendants] + [process.pid]:
        try:
            groups.add(os.getpgid(pid))
        except ProcessLookupError:
            pass
    for pgid in groups:
        if pgid != os.getpgrp():
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    process.join(timeout=5)


def measure(root: Path, private_root: Path) -> list[dict]:
    """Run sequentially once only.  Preserve failures as rows, never retune."""
    root, private_root = root.resolve(), private_root.resolve()
    if private_root == REPO or private_root.is_relative_to(REPO):
        raise ValueError("private work must remain outside repository")
    manifest = verify_freeze(root)
    if private_root.exists() or (root / "results.json").exists():
        raise FileExistsError("no overwrite or resume of physical measurements")
    private_root.mkdir(parents=True)
    models = _nangate_models(private_root, manifest)
    pair_seeds = {(row["family"], row["parameter"]):
                  (secrets.randbits(128), secrets.token_hex(16)) for row in manifest["cases"]}
    seeds_file = private_root / "private-replay-seeds.json"
    with seeds_file.open("x") as stream:
        os.chmod(seeds_file, 0o600)
        json.dump({f"{f}:{n}": {"seed": seed, "seed_id": seed_id}
                   for (f, n), (seed, seed_id) in pair_seeds.items()}, stream)
    results = []
    for row in manifest["cases"]:
        name = row["case"]
        work = _run_dir(private_root, name)
        seed, seed_id = pair_seeds[(row["family"], row["parameter"])]
        answer: multiprocessing.Queue = multiprocessing.Queue(maxsize=1)
        process = multiprocessing.Process(target=_measure_one,
            args=(row, root, work, models, manifest, seed, seed_id, answer))
        started = time.monotonic()
        process.start()
        process.join(timeout=CASE_WALL_S)
        if process.is_alive():
            _kill_case_tree(process)
            record = _empty_record(row, manifest, seed_id)
            record["physical_stage"] = "timed_out"
            record["error"] = "TimeoutError at case_wall_cap"
            record["elapsed_s"] = round(time.monotonic() - started, 3)
        else:
            try:
                record = answer.get(timeout=2)
            except Empty:
                record = _empty_record(row, manifest, seed_id)
                record["error"] = "CaseWorkerError"
                record["elapsed_s"] = round(time.monotonic() - started, 3)
        results.append(record)
        # Publish only compact metrics and case status.  The log and seed tree
        # remains in the owner-provided private directory.
        (root / "results.json").write_text(json.dumps({"schema": "pilot-physical-results-v1",
            "freeze_sha256": manifest["freeze_sha256"], "cases": results}, indent=2) + "\n")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "verify", "measure"))
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--private-work", type=Path)
    args = parser.parse_args(argv)
    if args.action == "freeze":
        report = freeze(args.evidence)
        print(json.dumps({"freeze_sha256": report["freeze_sha256"], "cases": len(report["cases"])}, indent=2))
    elif args.action == "verify":
        report = verify_freeze(args.evidence)
        print(json.dumps({"freeze_sha256": report["freeze_sha256"], "verified": True}, indent=2))
    else:
        if args.private_work is None:
            parser.error("measure requires --private-work outside repository")
        report = measure(args.evidence, args.private_work)
        print(json.dumps({"freeze_sha256": verify_freeze(args.evidence)["freeze_sha256"],
                          "cases": len(report), "reported": sum(r["physical_stage"] == "post_route_report" for r in report)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
