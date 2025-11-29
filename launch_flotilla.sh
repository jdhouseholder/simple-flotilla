#!/bin/bash

set -euo pipefail

# Start your background jobs
uv run ./src/simple_flotilla/worker.py --cfg_path=./cfg/worker.0.toml &
uv run ./src/simple_flotilla/worker.py --cfg_path=./cfg/worker.1.toml &
uv run ./src/simple_flotilla/worker.py --cfg_path=./cfg/worker.2.toml &

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
