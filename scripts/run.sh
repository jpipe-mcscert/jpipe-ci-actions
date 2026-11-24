#!/usr/bin/env bash
# Run jpipe-runner on a justification, and keep what it wrote for the steps after it.
#
# Environment (each front end maps its inputs to these):
#   JPIPE_PYTHON          Python interpreter that runs jpipe-runner (default: python3)
#   JPIPE_JUSTIFICATION   The justification, as the JSON file the jPipe compiler writes
#   JPIPE_LIBRARY         Step libraries, one per line (files or quoted globs)
#   JPIPE_PYTHON_PATH     Directories the libraries import modules from, one per line
#   JPIPE_STRICT          "true" counts validation warnings as errors, and fails a skip
#   JPIPE_DRY_RUN         "true" validates the libraries and calls no step
#   JPIPE_JOBS            Steps run at a time: a number, or auto; empty: the runner's default
#   JPIPE_VERBOSITY       quiet, normal (the default), verbose or debug; another value
#                         is a usage error, exit code 2
#   JPIPE_DIAGRAM_FORMAT  Format of the diagram (svg, png, pdf, dot, ...); empty: none
#   JPIPE_SUFFIX          Appended to the diagram's name, such as a commit SHA
#   JPIPE_OUTPUT_DIR      Directory the report, the logs and the diagram are written to
#   JPIPE_OUTPUTS         File that receives the outputs, one `key=value` per line
#
# Outputs: result (the runner's exit code), verdict, report, text, log, diagram. The
# verdict is empty when the report's schema is one this action does not read (report.py).
# The paths are absolute; one the run did not write is left empty.
#
# The command is an array: every value reaches jpipe-runner as one literal argument, and
# is never parsed by the shell (no eval). Platform-neutral (docs/adr/0001).
set -uo pipefail

python="${JPIPE_PYTHON:-python3}"
output_dir="${JPIPE_OUTPUT_DIR:?JPIPE_OUTPUT_DIR is required}"
outputs="${JPIPE_OUTPUTS:?JPIPE_OUTPUTS is required}"
justification="${JPIPE_JUSTIFICATION:?JPIPE_JUSTIFICATION is required}"
format="${JPIPE_DIAGRAM_FORMAT:-}"

mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd)"
report="$output_dir/report.json"
text="$output_dir/report.txt"
log="$output_dir/log.txt"

name="$(basename "$justification")"
name="${name%.*}${JPIPE_SUFFIX:+-$JPIPE_SUFFIX}"
diagram=""

command=("$python" -m jpipe_runner)
while IFS= read -r line; do
  [[ -n "$line" ]] && command+=(--library "$line")
done <<< "${JPIPE_LIBRARY:-}"
while IFS= read -r line; do
  [[ -n "$line" ]] && command+=(--python-path "$line")
done <<< "${JPIPE_PYTHON_PATH:-}"
[[ "${JPIPE_STRICT:-false}" == "true" ]] && command+=(--strict)
[[ "${JPIPE_DRY_RUN:-false}" == "true" ]] && command+=(--dry-run)
[[ -n "${JPIPE_JOBS:-}" ]] && command+=(--jobs "$JPIPE_JOBS")
# A value the runner would not get is a usage error, reported as the runner reports one.
usage=""
case "${JPIPE_VERBOSITY:-normal}" in
  quiet) command+=(-q) ;;
  normal) ;;
  verbose) command+=(-v) ;;
  debug) command+=(-vv) ;;
  *) usage="error: verbosity must be quiet, normal, verbose or debug, not '$JPIPE_VERBOSITY'" ;;
esac
if [[ -n "$format" ]]; then
  diagram="$output_dir/$name.$format"
  command+=(--diagram "$diagram")
fi
command+=(--report "$report" --colour never "$justification")

# A file left by an earlier run in the same folder would be reported as this run's.
rm -f -- "$report" "$text" "$log" ${diagram:+"$diagram"}

if [[ -n "$usage" ]]; then
  : > "$text"
  echo "$usage" > "$log"
  result=2
  echo "jpipe-runner not run: usage error (exit code $result)"
else
  # %q shows each argument as the shell would need it quoted, so the log is unambiguous.
  printf 'Running:'
  printf ' %q' "${command[@]}"
  printf '\n'
  "${command[@]}" > "$text" 2> "$log"
  result=$?
  echo "jpipe-runner exited with code $result"
fi
cat "$log" "$text"

# A file the run did not write is not reported: a usage error writes nothing, and a
# diagram that could not be drawn is not there.
existing() {
  if [[ -n "$1" && -f "$1" ]]; then printf '%s' "$1"; fi
}
# Empty, with a warning, for a report whose schema this action does not read.
verdict="$("$python" "$(dirname "${BASH_SOURCE[0]}")/report.py" verdict "$report")"

{
  echo "result=$result"
  echo "verdict=$verdict"
  echo "report=$(existing "$report")"
  echo "text=$text"
  echo "log=$log"
  echo "diagram=$(existing "$diagram")"
} >> "$outputs"

# The runner's exit code is an output, not this script's: the front end reports the run
# before it fails the job.
exit 0
