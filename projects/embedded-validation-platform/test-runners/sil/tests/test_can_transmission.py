from embedded_models import CANTransmitter


def test_sw_009_can_transmission():
    transmitter = CANTransmitter()

    assert transmitter.send(0x123, [1, 2, 3]) is True
    assert transmitter.send(0x800, [1, 2]) is False
    assert transmitter.send(0x123, list(range(9))) is False

    assert len(transmitter.sent_messages) == 1
