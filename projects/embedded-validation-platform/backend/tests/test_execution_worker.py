from unittest.mock import Mock
from execution_worker import Worker, execute_sil


def test_unknown_test_rejected():
    assert execute_sil("unknown")[0] == "ERROR"


def test_empty_queue():
    queue = Mock()
    queue.claim.return_value = None
    runner = Mock()
    assert Worker(queue, "worker", runner).cycle() is False
    runner.assert_not_called()


def test_fenced_completion():
    queue = Mock()
    queue.claim.return_value = {"id": 1, "test_id": "TC-004", "lease_token": "lease"}
    runner = Mock(return_value=("PASSED", 0.1, "ok"))
    assert Worker(queue, "worker", runner).cycle()
    queue.finish.assert_called_once_with(1, "lease", "PASSED", 0.1, "ok")


def test_stopped_worker_does_not_claim():
    queue = Mock()
    worker = Worker(queue, "worker")
    worker.stop.set()
    assert not worker.cycle()
    queue.claim.assert_not_called()
