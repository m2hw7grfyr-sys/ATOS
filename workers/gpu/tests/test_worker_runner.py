import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from worker.config import WorkerConfig
from worker.runner import GPUWorker


class FakeMain:
    def __init__(self):
        self.failed = []
        self.completed = []
        self.started = []
        self.task = {
            "id": 1,
            "prompt": "hello",
            "system_prompt": None,
            "model": "llama3.1:8b",
            "options": {},
        }

    def lease_task(self):
        task = self.task
        self.task = None
        return task

    def mark_started(self, task_id):
        self.started.append(task_id)

    def complete_task(self, task_id, result_text, metrics):
        self.completed.append((task_id, result_text, metrics))

    def fail_task(self, task_id, error_message, error_type, retryable=True):
        self.failed.append((task_id, error_message, error_type, retryable))


class FailingOllama:
    def generate(self, *_args, **_kwargs):
        raise RuntimeError("ollama unavailable")


class WorkerRunnerTest(unittest.TestCase):
    def test_ollama_failure_reports_failed_task_without_exiting(self):
        config = WorkerConfig(
            main_url="http://127.0.0.1:8080",
            api_key="test",
            worker_id="worker-test",
            worker_name="worker-test",
            worker_type="gpu",
            ollama_url="http://127.0.0.1:11434",
            model_name="llama3.1:8b",
            heartbeat_interval_seconds=10,
            poll_interval_seconds=1,
            request_timeout_seconds=1,
            generation_timeout_seconds=1,
            supported_models=["llama3.1:8b"],
            log_level="CRITICAL",
        )
        worker = GPUWorker(config)
        fake_main = FakeMain()
        worker.main = fake_main
        worker.ollama = FailingOllama()

        handled = worker.run_once()

        self.assertTrue(handled)
        self.assertEqual(fake_main.started, [1])
        self.assertEqual(len(fake_main.failed), 1)
        self.assertEqual(fake_main.failed[0][2], "RuntimeError")
        self.assertEqual(worker.state.status, "idle")
        self.assertIsNone(worker.state.current_task_id)


if __name__ == "__main__":
    unittest.main()
