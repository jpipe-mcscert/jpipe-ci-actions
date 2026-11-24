#!/usr/bin/env bash
# Install what drawing the diagram needs, when it is missing: Graphviz's dot, and for a
# format other than svg, a font with the status symbols.
#
# Environment:
#   JPIPE_DIAGRAM_FORMAT  The diagram's format; empty (no diagram) or dot needs nothing
#   JPIPE_WARNING         What a warning line starts with (default: "warning: "), such as
#                         a front end's annotation syntax
#
# Installs with apt-get, as root or through sudo; elsewhere it warns, and the runner says
# whether the diagram could be drawn. Platform-neutral (docs/adr/0001).
set -euo pipefail

format="${JPIPE_DIAGRAM_FORMAT:-}"
[[ -n "$format" && "$format" != "dot" ]] || exit 0

warn() {
  echo "${JPIPE_WARNING-warning: }$1"
}

packages=()
command -v dot > /dev/null || packages+=(graphviz)
# The diagram marks each status with a symbol (✔ ✘ ◌ ⚠). An SVG leaves them to the
# browser; any other format draws them with a font installed here, and without one that
# has them, they come out as empty boxes. The list is read whole: grep -q stopping early
# must not make fc-list fail under pipefail.
fonts="$(fc-list : family 2> /dev/null || true)"
if [[ "$format" != "svg" ]] && ! grep -qi "DejaVu Sans" <<< "$fonts"; then
  packages+=(fonts-dejavu-core)
fi

if (( ${#packages[@]} )); then
  sudo=()
  (( EUID == 0 )) || sudo=(sudo)
  if ! command -v apt-get > /dev/null || { (( ${#sudo[@]} )) && ! command -v sudo > /dev/null; }; then
    warn "cannot install ${packages[*]} here (no apt-get, or not root and no sudo): the $format diagram may not be drawn, or its status symbols may show as empty boxes"
    exit 0
  fi
  "${sudo[@]}" env DEBIAN_FRONTEND=noninteractive apt-get update -qq
  "${sudo[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends "${packages[@]}" > /dev/null
  echo "Installed: ${packages[*]}"
fi
echo "Graphviz: $(dot -V 2>&1)"
