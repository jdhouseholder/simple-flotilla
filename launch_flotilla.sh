#!/bin/bash

set -euo pipefail

# Start your background jobs
uv run -m simple_flotilla.worker --cfg_path=./cfg/worker.0.toml &
uv run -m simple_flotilla.worker --cfg_path=./cfg/worker.1.toml &
uv run -m simple_flotilla.worker --cfg_path=./cfg/worker.2.toml &

# On Ctrl-C (SIGINT) or SIGTERM, kill the entire process group
cleanup() {
  echo "Stopping all background processes..."
  trap - INT TERM
  kill -TERM -- -$$ 2>/dev/null || true
  wait || true
  exit 130
}
trap cleanup INT TERM

wait
