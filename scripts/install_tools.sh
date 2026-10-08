#!/usr/bin/env bash
# Debian 13 local tool install. Downloads packages but never modifies /usr or /etc.
set -euo pipefail
prefix="${1:-$PWD/.tools}"
mkdir -p "$prefix/debs" "$prefix/apt/lists/partial" "$prefix/apt/cache/archives/partial"
prefix="$(cd "$prefix" && pwd)"
printf 'deb https://deb.debian.org/debian trixie main\n' > "$prefix/sources.list"
opts=(-o "Dir::Etc::sourcelist=$prefix/sources.list" -o Dir::Etc::sourceparts=- -o "Dir::State=$prefix/apt" -o "Dir::Cache=$prefix/apt/cache" -o "APT::Sandbox::User=$(id -un)")
apt-get "${opts[@]}" update
cd "$prefix/debs"
apt-get "${opts[@]}" download iverilog=12.0-2+b1 yosys=0.52-2 yosys-abc=0.52-2
for f in ./*.deb; do dpkg-deb -x "$f" "$prefix/root"; done
sha256sum ./*.deb > "$prefix/deb-sha256.txt"
printf 'export CHIP_RL_TOOLS=%q\nexport PATH=%q/bin:$PATH\n' "$prefix/root/usr" "$prefix/root/usr" > "$prefix/env.sh"
printf 'Installed locally. Run: source %s/env.sh\n' "$prefix"
