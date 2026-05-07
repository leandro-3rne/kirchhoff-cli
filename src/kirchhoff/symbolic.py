import sympy as sp
import re
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    convert_xor,
    implicit_multiplication_application,
    function_exponentiation,
    auto_symbol,
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
    "sqrt",
)


def _normalize_math_input(expr: str, variable_name: str) -> str:
    text = expr.strip()
    for fn_name in IMPLICIT_ARG_FUNCTIONS:
        pattern = rf"\b{fn_name}\b(?!\s*\()"
        text = re.sub(pattern, f"{fn_name}({variable_name})", text)
    return text


def _sympify_with_complex_j(
    expr: str, variable_symbol: sp.Symbol
) -> sp.Expr:
    normalized = _normalize_math_input(expr, variable_symbol.name)
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
        "sqrt": sp.sqrt,
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
        # Fallback for simple constants/symbols that should still be valid,
        # e.g. "a" or "5".
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
    fs_obj = sp.fourier_series(expr, (x, -interval_half, interval_half))
    partial_sum = sp.expand_trig(fs_obj.truncate(order + 1))

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