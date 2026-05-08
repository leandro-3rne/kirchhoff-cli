import pytest

from kirchhoff.resistance import equivalent_impedance, equivalent_resistance


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


def test_impedance_parallel_complex_values():
    result = equivalent_impedance("(5 + 8j) || (6 - 1/8j)", mode="z", omega=1.0)
    expected = 1 / (1 / (5 + 8j) + 1 / (6 - 1 / 8j))
    assert result == pytest.approx(expected)


def test_impedance_with_omega_and_inductor_formula():
    result = equivalent_impedance("3ohm || jomega3kH", mode="z", omega=5.0)
    expected = 1 / (1 / 3 + 1 / (1j * 5 * 3000))
    assert result == pytest.approx(expected)


def test_impedance_with_divided_jomega_terms():
    result = equivalent_impedance("7 - jomega4H/-jomega8kH", mode="z", omega=2.0)
    expected = 7 - (1j * 2 * 4) / (-1j * 2 * 8000)
    assert result == pytest.approx(expected)


def test_capacitor_mode_requires_omega():
    with pytest.raises(ValueError):
        equivalent_impedance("5 + 3f", mode="c")


def test_capacitor_mode_with_omega():
    omega = 10.0
    result = equivalent_impedance("5 + 3f", mode="c", omega=omega)
    expected = 1 / (1j * omega * 5) + 1 / (1j * omega * 3)
    assert result == pytest.approx(expected)


def test_inductor_mode_with_omega_and_parallel():
    omega = 2.0
    result = equivalent_impedance("5h || 8kH", mode="l", omega=omega)
    expected = 1 / (1 / (1j * omega * 5) + 1 / (1j * omega * 8000))
    assert result == pytest.approx(expected)


def test_passive_modes_reject_subtraction():
    with pytest.raises(ValueError):
        equivalent_impedance("5h - 3h", mode="l", omega=10.0)
    with pytest.raises(ValueError):
        equivalent_impedance("5f - 3f", mode="c", omega=10.0)
    with pytest.raises(ValueError):
        equivalent_impedance("5ohm - 3ohm", mode="r")


def test_passive_modes_reject_symbolic_terms():
    with pytest.raises(ValueError):
        equivalent_impedance("jomega3h", mode="l", omega=10.0)
    with pytest.raises(ValueError):
        equivalent_impedance("jfreq2 - jfreq3", mode="c", omega=10.0)
