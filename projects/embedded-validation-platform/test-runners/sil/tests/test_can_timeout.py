from can_monitor import CANMonitor


def test_sw_004_can_timeout():
    monitor = CANMonitor(timeout_ms=500)

    monitor.receive_message(1000)

    assert monitor.communication_lost(1400) is False
    assert monitor.communication_lost(1500) is True
