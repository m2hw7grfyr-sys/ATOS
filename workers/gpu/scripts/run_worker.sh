#!/usr/bin/env bash
set -euo pipefail

cd /workspace/atos-gpu-worker
exec python3 main.py --config /workspace/config/gpu-worker.env
