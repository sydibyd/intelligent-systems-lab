from execution_api import classify_pytest_result


def test_success_is_passed():
    assert classify_pytest_result(0) == "PASSED"


def test_assertion_failure_is_failed():
    assert classify_pytest_result(1) == "FAILED"


def test_pytest_usage_error():
    assert classify_pytest_result(4) == "ERROR"


def test_pytest_internal_error():
    assert classify_pytest_result(3) == "ERROR"


def test_process_termination():
    assert classify_pytest_result(-9) == "ERROR"
