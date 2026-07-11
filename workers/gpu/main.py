from __future__ import annotations

import argparse
import sys

from worker.config import WorkerConfig
from worker.logging_setup import configure_logging
from worker.runner import GPUWorker, install_signal_handlers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ATOS GPU Worker")
    parser.add_argument("--config", default=None, help="Path to gpu-worker.env")
    parser.add_argument("--status", action="store_true", help="Check configuration and Ollama status, then exit")
    parser.add_argument("--once", action="store_true", help="Process at most one leased task, then exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = WorkerConfig.load(args.config)
    configure_logging(config.log_level)
    worker = GPUWorker(config)
    if args.status:
        errors = worker.check_ready()
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("GPU Worker ready")
        return 0
    errors = config.validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    install_signal_handlers(worker)
    if args.once:
        worker.start_heartbeat()
        worker.run_once()
        return 0
    worker.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
