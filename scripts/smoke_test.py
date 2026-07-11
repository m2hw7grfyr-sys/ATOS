from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from argparse import ArgumentParser


BASE_URL = ""
API_PREFIX = ""
OPTIONAL_URLS = {"frontend": "", "worker": ""}


def candidate_paths(path: str) -> list[str]:
    paths = [path]
    if API_PREFIX:
        paths.append(f"/{API_PREFIX}{path}")
    paths.append(f"/api{path}")
    return list(dict.fromkeys(paths))


def get_json(path: str) -> dict:
    url = f"{BASE_URL.rstrip('/')}{path}"
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def check_api(name: str, path: str, *, required: bool = True) -> bool:
    last_error = None
    try:
        for candidate in candidate_paths(path):
            try:
                payload = get_json(candidate)
                ok = bool(payload.get("success")) and payload.get("data") is not None
                print(f"[{'OK' if ok else 'FAIL'}] {name}: {candidate}")
                return ok
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code == 404:
                    continue
                raise
    except Exception as exc:
        last_error = exc
    print(f"[{'FAIL' if required else 'WARN'}] {name}: {path} -> {last_error}")
    return not required


def check_url(name: str, url: str, *, required: bool = False) -> bool:
    if not url:
        print(f"[SKIP] {name}: not configured")
        return True
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            ok = 200 <= response.status < 500
        print(f"[{'OK' if ok else 'FAIL'}] {name}: {url}")
        return ok
    except urllib.error.URLError as exc:
        print(f"[{'FAIL' if required else 'WARN'}] {name}: {url} -> {exc}")
        return not required


def parse_args() -> None:
    global API_PREFIX, BASE_URL, OPTIONAL_URLS

    parser = ArgumentParser(description="Run ATOS production smoke checks.")
    parser.add_argument("--api-base-url", default=os.getenv("ATOS_BASE_URL") or os.getenv("API_BASE_URL") or "http://127.0.0.1:8000")
    parser.add_argument("--api-prefix", default=os.getenv("ATOS_API_PREFIX", ""))
    parser.add_argument("--frontend-url", default=os.getenv("FRONTEND_URL", "http://127.0.0.1:5173"))
    parser.add_argument("--worker-url", default=os.getenv("WORKER_URL", ""))
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-worker", action="store_true")
    args = parser.parse_args()
    BASE_URL = args.api_base_url
    API_PREFIX = args.api_prefix.strip("/")
    OPTIONAL_URLS = {
        "frontend": "" if args.skip_frontend else args.frontend_url,
        "worker": "" if args.skip_worker else args.worker_url,
    }


def main() -> int:
    parse_args()
    checks = [
        check_api("backend health", "/health"),
        check_api("database health", "/health/database"),
        check_api("redis health", "/health/redis", required=False),
        check_api("worker health", "/health/worker", required=False),
        check_api("scheduler health", "/health/scheduler"),
        check_api("ai runtime mock", "/health/ai-runtime"),
        check_api("browser runtime mock", "/health/browser-runtime"),
        check_api("submission runtime mock", "/submission/dashboard"),
        check_api("readiness", "/ready"),
        check_api("liveness", "/live"),
        check_api("metrics", "/metrics"),
        check_url("frontend reachable", OPTIONAL_URLS["frontend"], required=False),
        check_url("worker reachable", OPTIONAL_URLS["worker"], required=False),
    ]
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
