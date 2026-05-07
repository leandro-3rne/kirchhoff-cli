import pytest

from kirchhoff.units import parse_value, format_si


def test_parse_si_prefixes():
    assert parse_value("1k") == 1000
    assert parse_value("4.7k") == 4700
    assert parse_value("10m") == 0.01
    assert parse_value("100n") == pytest.approx(1e-7)
    assert parse_value("6e-3") == 0.006
    assert parse_value("2T") == 2e12


def test_parse_units():
    assert parse_value("4.7kohm", "ohm") == 4700
    assert parse_value("10mA", "A") == 0.01
    assert parse_value("100nF", "F") == pytest.approx(1e-7)
    assert parse_value("10mH", "H") == 0.01
    assert parse_value("2ms", "s") == pytest.approx(0.002)


def test_invalid_unit():
    with pytest.raises(ValueError):
        parse_value("10kg", "ohm")


def test_format_si():
    assert format_si(4700, "Ω") == "4.7 kΩ"
    assert format_si(0.001, "s") == "1 ms"