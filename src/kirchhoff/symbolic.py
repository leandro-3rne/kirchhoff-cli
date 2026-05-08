import re

import sympy as sp
from sympy.calculus.util import periodicity
from sympy.parsing.sympy_parser import (
    auto_symbol,
    convert_xor,
    function_exponentiation,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


IMPLICIT_ARG_FUNCTIONS = (
    "sin",
    "cos",
    "tan",
    "sinh",
    "cosh",
    "tanh",
    "exp",
    "log",
    "ln",
    "sqrt",
    "square",
    "sawtooth",
    "triangle",
    "heaviside",
)


def _normalize_math_input(expr: str, variable_name: str) -> str:
    text = expr.strip()
    for fn_name in IMPLICIT_ARG_FUNCTIONS:
        # Accept shorthand like sinx, cosx, coshx, expx (for current variable).
        suffix_pattern = rf"\b{fn_name}{variable_name}\b"
        text = re.sub(suffix_pattern, f"{fn_name}({variable_name})", text)
        pattern = rf"\b{fn_name}\b(?!\s*\()"
        text = re.sub(pattern, f"{fn_name}({variable_name})", text)
    return text


def _sympify_with_complex_j(expr: str, variable_symbol: sp.Symbol) -> sp.Expr:
    normalized = _normalize_math_input(expr, variable_symbol.name)
    def _square(arg: sp.Expr) -> sp.Expr:
        # 2*pi-periodic square wave in {-1, 0, 1}
        return sp.sign(sp.sin(arg))

    def _sawtooth(arg: sp.Expr) -> sp.Expr:
        # 2*pi-periodic normalized sawtooth in [-1, 1).
        return 2 * (arg / (2 * sp.pi) - sp.floor(arg / (2 * sp.pi) + sp.Rational(1, 2)))

    def _triangle(arg: sp.Expr) -> sp.Expr:
        # 2*pi-periodic normalized triangle in [-1, 1].
        saw = _sawtooth(arg)
        return 2 * sp.Abs(saw) - 1

    locals_map = {
        "I": sp.I,
        "i": sp.I,
        "pi": sp.pi,
        "E": sp.E,
        "e": sp.E,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "exp": sp.exp,
        "log": sp.log,
        "ln": sp.log,
        "sqrt": sp.sqrt,
        "square": _square,
        "sawtooth": _sawtooth,
        "triangle": _triangle,
        "heaviside": sp.Heaviside,
        variable_symbol.name: variable_symbol,
    }
    if variable_symbol.name not in {"i", "I"}:
        locals_map["i"] = sp.I
        locals_map["I"] = sp.I
    if variable_symbol.name not in {"j", "J"}:
        locals_map["j"] = sp.I
        locals_map["J"] = sp.I
    if variable_symbol.name in {"e", "E"}:
        locals_map.pop("e", None)
        locals_map.pop("E", None)
    transformations = standard_transformations + (
        convert_xor,
        implicit_multiplication_application,
        function_exponentiation,
        auto_symbol,
    )
    try:
        return parse_expr(
            normalized,
            local_dict=locals_map,
            transformations=transformations,
            evaluate=True,
        )
    except Exception:
        try:
            return sp.sympify(normalized, locals=locals_map)
        except Exception as exc:
            raise ValueError(f"Invalid symbolic expression: {expr!r}") from exc


def taylor_series(
    expression: str,
    variable: str = "x",
    around: str = "0",
    order: int = 5,
    value: str | None = None,
) -> dict[str, sp.Expr | int | None]:
    """
    Compute a Taylor polynomial (and optional point evaluation).

    Supports complex expressions via `I`, `i`, and `j`.
    Also accepts `^` as power notation, e.g. `e^x`, `x^(1/2)`.
    """
    if order < 0:
        raise ValueError("order must be non-negative")

    x = sp.Symbol(variable)
    expr = _sympify_with_complex_j(expression, x)
    a = _sympify_with_complex_j(around, x)

    if expr.has(sp.floor, sp.Heaviside, sp.sign):
        raise ValueError(
            "Expression is not Taylor-compatible (contains discontinuous/non-smooth terms)."
        )

    # A Taylor expansion around `a` requires the function to be finite at `a`.
    value_at_a = sp.simplify(expr.subs(x, a))
    if value_at_a.is_finite is False or value_at_a.has(sp.zoo, sp.oo, -sp.oo, sp.nan):
        raise ValueError("Expression is not finite at the expansion point.")

    series = sp.series(expr, x, a, order + 1)
    polynomial = sp.expand(series.removeO())

    approximation = None
    true_value = None
    error = None

    if value is not None:
        v = _sympify_with_complex_j(value, x)
        approximation = sp.N(polynomial.subs(x, v))
        true_value = sp.N(expr.subs(x, v))
        error = sp.Abs(true_value - approximation)

    return {
        "expression": expr,
        "variable": x,
        "around": a,
        "order": order,
        "series": series,
        "polynomial": polynomial,
        "approximation": approximation,
        "true_value": true_value,
        "error": error,
    }


def fourier_series(
    expression: str,
    variable: str = "x",
    period: str = "2*pi",
    order: int = 5,
    value: str | None = None,
) -> dict[str, sp.Expr | int | None]:
    """
    Compute a truncated Fourier series (and optional point evaluation).

    Supports complex expressions via `I`, `i`, and `j`.
    Also accepts `^` as power notation, e.g. `e^x`, `x^(1/2)`.
    """
    if order < 0:
        raise ValueError("order must be non-negative")

    x = sp.Symbol(variable)
    expr = _sympify_with_complex_j(expression, x)
    T = _sympify_with_complex_j(period, x)

    t_numeric = sp.N(T)
    if t_numeric.is_real is False:
        raise ValueError("period must be real")
    if t_numeric.is_real and float(t_numeric) <= 0:
        raise ValueError("period must be positive")

    interval_half = sp.simplify(T / 2)
    expr_period = periodicity(expr, x)
    if expr_period is None and not expr.is_polynomial(x):
        raise ValueError(
            "Expression is not periodic (or periodicity cannot be determined) for Fourier series."
        )
    if expr_period is not None:
        ratio = sp.simplify(T / expr_period)
        if ratio.is_integer is False:
            raise ValueError("Provided period is incompatible with expression periodicity.")

    if expr.has(sp.cosh(x), sp.sinh(x), sp.tanh(x)):
        raise ValueError("Expression is not periodic for the provided period.")

    try:
        fs_obj = sp.fourier_series(expr, (x, -interval_half, interval_half))
        partial_sum = fs_obj.truncate(order + 1)
    except Exception:
        # Robust fallback for complex-valued expressions:
        # compute Fourier series of real and imaginary parts separately.
        real_fs = sp.fourier_series(sp.re(expr), (x, -interval_half, interval_half))
        imag_fs = sp.fourier_series(sp.im(expr), (x, -interval_half, interval_half))
        fs_obj = None
        partial_sum = real_fs.truncate(order + 1) + sp.I * imag_fs.truncate(order + 1)

    partial_sum = sp.simplify(sp.expand_trig(partial_sum))

    approximation = None
    true_value = None
    error = None

    if value is not None:
        v = _sympify_with_complex_j(value, x)
        approximation = sp.N(partial_sum.subs(x, v))
        true_value = sp.N(expr.subs(x, v))
        error = sp.Abs(true_value - approximation)

    return {
        "expression": expr,
        "variable": x,
        "period": T,
        "order": order,
        "series": fs_obj,
        "polynomial": partial_sum,
        "approximation": approximation,
        "true_value": true_value,
        "error": error,
    }
