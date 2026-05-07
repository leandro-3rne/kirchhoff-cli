import math
import pytest

from kirchhoff.circuits import ohm, power, rc, rl, voltage_divider, current_divider


def test_ohm_calculates_current():
    result = ohm(v=5, r=220)

    assert result["v"] == 5
    assert result["r"] == 220
    assert result["i"] == pytest.approx(5 / 220)
    assert result["p"] == pytest.approx(5 * (5 / 220))


def test_ohm_calculates_voltage():
    result = ohm(i=0.02, r=100)

    assert result["v"] == pytest.approx(2)
    assert result["i"] == pytest.approx(0.02)
    assert result["r"] == pytest.approx(100)
    assert result["p"] == pytest.approx(0.04)


def test_ohm_calculates_resistance():
    result = ohm(v=5, i=0.01)

    assert result["r"] == pytest.approx(500)
    assert result["p"] == pytest.approx(0.05)


def test_ohm_requires_exactly_two_values():
    with pytest.raises(ValueError):
        ohm(v=5)

    with pytest.raises(ValueError):
        ohm(v=5, i=0.01, r=500)


def test_power_from_voltage_and_current():
    result = power(v=5, i=0.02)

    assert result["p"] == pytest.approx(0.1)
    assert result["r"] == pytest.approx(250)


def test_power_from_current_and_resistance():
    result = power(i=0.01, r=1000)

    assert result["p"] == pytest.approx(0.1)
    assert result["v"] == pytest.approx(10)


def test_rc_basic_values():
    result = rc(r=10_000, c=100e-9)

    assert result["tau"] == pytest.approx(0.001)
    assert result["fc"] == pytest.approx(1 / (2 * math.pi * 0.001))
    assert "formula" in result


def test_rc_transient_value():
    result = rc(r=10_000, c=100e-9, vin=5, v0=0, t=0.002)

    expected = 5 + (0 - 5) * math.exp(-0.002 / 0.001)

    assert result["vf"] == pytest.approx(5)
    assert result["vt"] == pytest.approx(expected)


def test_rl_basic_values():
    result = rl(r=100, l=10e-3)

    assert result["tau"] == pytest.approx(0.0001)
    assert result["fc"] == pytest.approx(100 / (2 * math.pi * 10e-3))
    assert "formula" in result


def test_rl_transient_value():
    result = rl(r=100, l=10e-3, vin=5, i0=0, t=0.001)

    i_final = 5 / 100
    expected = i_final + (0 - i_final) * math.exp(-0.001 / 0.0001)

    assert result["if"] == pytest.approx(i_final)
    assert result["it"] == pytest.approx(expected)


def test_voltage_divider():
    result = voltage_divider(vin=5, r1=10_000, r2=4_700)

    expected_v1 = 5 * 10000 / (10000 + 4700)
    expected_v2 = 5 * 4700 / (10000 + 4700)

    assert result["v1"] == pytest.approx(expected_v1)
    assert result["v2"] == pytest.approx(expected_v2)
    assert result["ratio"] == pytest.approx(expected_v2 / 5)


def test_current_divider():
    result = current_divider(iin=0.01, r1=100, r2=220)

    expected_i1 = 0.01 * 220 / (100 + 220)
    expected_i2 = 0.01 * 100 / (100 + 220)

    assert result["i1"] == pytest.approx(expected_i1)
    assert result["i2"] == pytest.approx(expected_i2)
    assert result["ratio"] == pytest.approx(expected_i2 / 0.01)
