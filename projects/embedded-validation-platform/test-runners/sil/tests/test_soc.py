import pytest
from embedded_models import SOCModel


def test_sw_011_soc_calculation():
    model = SOCModel()

    assert model.calculate(50, 100) == 50
    assert model.calculate(0, 100) == 0
    assert model.calculate(120, 100) == 100

    with pytest.raises(ValueError):
        model.calculate(50, 0)
