import pytest

from kirchhoff.resistance import equivalent_resistance


def test_series_resistance():
    assert equivalent_resistance("100 + 220") == pytest.approx(320)


def test_parallel_resistance():
    assert equivalent_resistance("200 || 300") == pytest.approx(120)


def test_series_and_parallel():
    assert equivalent_resistance("1k + (2k || 3k)") == pytest.approx(2200)


def test_multiple_parallel():
    expected = 1 / (1 / 100 + 1 / 220 + 1 / 330)
    assert equivalent_resistance("100 || 220 || 330") == pytest.approx(expected)

def test_units():
    assert equivalent_resistance("1kohm + 500ohm") == pytest.approx(1500)


def test_scientific_notation():
    assert equivalent_resistance("6e-3 + 2e-3") == pytest.approx(0.008)


def test_invalid_expression():
    with pytest.raises(ValueError):
        equivalent_resistance("1k +")
