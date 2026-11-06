from embedded_models import StartupController


def test_sw_008_startup_initialization():
    controller = StartupController()

    assert controller.initialize(12.0, 25.0) == "READY"
    assert controller.initialize(8.0, 25.0) == "ERROR"
    assert controller.initialize(12.0, 90.0) == "ERROR"
