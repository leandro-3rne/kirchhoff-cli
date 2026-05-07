import pytest
import sympy as sp

from kirchhoff.symbolic import taylor_series, fourier_series


def test_taylor_series_polynomial_for_exp():
    result = taylor_series("exp(x)", order=3)
    x = sp.Symbol("x")
    assert sp.simplify(result["polynomial"] - (1 + x + x**2 / 2 + x**3 / 6)) == 0


def test_taylor_series_with_point_evaluation():
    result = taylor_series("sin(x)", order=5, value="0.2")
    assert result["approximation"] is not None
    assert result["true_value"] is not None
    assert float(result["error"]) < 1e-5


def test_taylor_series_supports_complex_j():
    result = taylor_series("exp(j*x)", around="0", order=2, value="1.0")
    assert result["approximation"] is not None
    assert result["true_value"] is not None
    assert complex(result["true_value"]).imag == pytest.approx(
        complex(sp.N(sp.exp(sp.I))).imag
    )


def test_taylor_series_supports_complex_i():
    result = taylor_series("exp(i*x)", around="0", order=2, value="1.0")
    assert result["true_value"] is not None
    assert complex(result["true_value"]).imag == pytest.approx(
        complex(sp.N(sp.exp(sp.I))).imag
    )


def test_taylor_series_supports_caret_power_notation():
    result = taylor_series("e^x", around="0", order=3)
    x = sp.Symbol("x")
    assert sp.simplify(result["polynomial"] - (1 + x + x**2 / 2 + x**3 / 6)) == 0


def test_taylor_series_supports_root_as_power():
    result = taylor_series("x^(1/2)", around="1", order=2, value="1.21")
    assert result["true_value"] is not None
    assert complex(result["true_value"]).real == pytest.approx(1.1, rel=1e-10)


def test_taylor_series_supports_implicit_multiplication_and_cosh():
    result = taylor_series("exp(2x) + sin(x)*cosh(x)", order=3)
    x = sp.Symbol("x")
    expected = sp.expand((sp.exp(2 * x) + sp.sin(x) * sp.cosh(x)).series(x, 0, 4).removeO())
    assert sp.simplify(result["polynomial"] - expected) == 0


def test_taylor_series_rejects_unclosed_parenthesis():
    with pytest.raises(ValueError):
        taylor_series("exp(2x) + sin(x)*cosh(")


def test_taylor_series_rejects_negative_order():
    with pytest.raises(ValueError):
        taylor_series("x", order=-1)


def test_taylor_series_treats_other_symbols_as_constants():
    result = taylor_series("y*x + y^2", variable="x", around="0", order=1)
    x = sp.Symbol("x")
    y = sp.Symbol("y")
    assert sp.simplify(result["polynomial"] - (y**2 + y * x)) == 0


def test_taylor_series_accepts_constant_symbol_expression():
    result = taylor_series("a", variable="x", around="0", order=3, value="2")
    a = sp.Symbol("a")
    assert sp.simplify(result["polynomial"] - a) == 0
    assert sp.simplify(result["expression"] - a) == 0


def test_taylor_series_accepts_function_name_shorthand():
    result = taylor_series("sin + cosh", variable="x", around="0", order=3)
    x = sp.Symbol("x")
    expected_expr = sp.sin(x) + sp.cosh(x)
    expected_poly = sp.expand(expected_expr.series(x, 0, 4).removeO())
    assert sp.simplify(result["expression"] - expected_expr) == 0
    assert sp.simplify(result["polynomial"] - expected_poly) == 0


def test_fourier_series_basic_square_wave_form():
    result = fourier_series("x", variable="x", period="2*pi", order=3)
    x = sp.Symbol("x")
    # first harmonics of odd function should be sine-only terms
    assert result["polynomial"].has(sp.sin(x))
    assert not result["polynomial"].has(sp.cos(x))


def test_fourier_series_with_value():
    result = fourier_series("sin(x)", period="2*pi", order=5, value="0.4")
    assert result["approximation"] is not None
    assert result["true_value"] is not None
    assert float(result["error"]) < 1e-8


def test_fourier_series_supports_caret_and_complex_i():
    result = fourier_series("e^(i*x)", period="2*pi", order=4, value="0.3")
    assert result["true_value"] is not None
    expected = sp.N(sp.exp(sp.I * sp.Rational(3, 10)))
    assert complex(result["true_value"]).real == pytest.approx(complex(expected).real)


def test_fourier_series_rejects_non_positive_period():
    with pytest.raises(ValueError):
        fourier_series("sin(x)", period="0", order=3)


def test_fourier_series_treats_other_symbols_as_constants():
    result = fourier_series("a*sin(x)", variable="x", period="2*pi", order=2)
    a = sp.Symbol("a")
    x = sp.Symbol("x")
    assert sp.simplify(result["polynomial"] - a * sp.sin(x)) == 0


def test_fourier_series_accepts_function_name_shorthand():
    result = fourier_series("cos", variable="x", period="2*pi", order=3)
    x = sp.Symbol("x")
    assert sp.simplify(result["expression"] - sp.cos(x)) == 0
    assert sp.simplify(result["polynomial"] - sp.cos(x)) == 0
