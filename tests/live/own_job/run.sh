#!/usr/bin/env bash
# Run one headless own-job round and measure it.
# usage: run.sh <name> [resume-session-id]
# env:   OWN_JOB_OUT     folder for <name>.jsonl and <name>.err (required)
#        OWN_JOB_PROMPT  prompt file (default: job.txt next to this script)
#        OWN_JOB_PYTHON  Python for analyze.py (default: <repo>/.venv-py3.14/bin/python;
#                        the system python3 links SQLite 3.40.1, a WAL-reset risk)
set -euo pipefail

if [ -z "${OWN_JOB_OUT:-}" ] || [ -z "${1:-}" ]; then
  echo "usage: OWN_JOB_OUT=<folder> run.sh <name> [resume-session-id]" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../../.." && pwd)"
name="$1"
resume="${2:-}"
prompt="${OWN_JOB_PROMPT:-$script_dir/job.txt}"
python_bin="${OWN_JOB_PYTHON:-$repo_root/.venv-py3.14/bin/python}"

mkdir -p "$OWN_JOB_OUT"
cd "$repo_root"

args=(chat --query-file "$prompt" --oneshot -Q --format stream-json)
if [ -n "$resume" ]; then
  args+=(--resume "$resume")
fi

code=0
timeout 300 hermes "${args[@]}" > "$OWN_JOB_OUT/$name.jsonl" 2> "$OWN_JOB_OUT/$name.err" || code=$?
echo "run=$name exit=$code"

analyze_code=0
"$python_bin" -I "$script_dir/analyze.py" --out "$OWN_JOB_OUT" "$name" || analyze_code=$?
exit "$analyze_code"
