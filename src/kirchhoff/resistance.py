import re
import sympy as sp
from sympy.parsing.sympy_parser import (
    auto_symbol,
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from kirchhoff.units import parse_value


_VALUE_WITH_SUFFIX_RE = re.compile(
    r"(?<![A-Za-z_])"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[A-Za-zµΩΩ]*)"
    r"(?![A-Za-z_])"
)


def _split_top_level(expr: str, sep: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    i = 0
    step = len(sep)
    while i < len(expr):
        ch = expr[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("Mismatched parentheses in expression.")
        elif depth == 0 and expr.startswith(sep, i):
            parts.append(expr[start:i].strip())
            i += step
            start = i
            continue
        i += 1
    if depth != 0:
        raise ValueError("Mismatched parentheses in expression.")
    parts.append(expr[start:].strip())
    if any(part == "" for part in parts):
        raise ValueError("Invalid network expression.")
    return parts


def _split_parallel(expr: str) -> list[str]:
    return _split_top_level(expr, "||")


def _as_complex(value: sp.Expr) -> complex:
    evaluated = complex(sp.N(value))
    if not (evaluated.real == evaluated.real and evaluated.imag == evaluated.imag):
        raise ValueError("Expression evaluated to an invalid complex value.")
    return evaluated


def _replace_literals(expr: str, mode: str) -> str:
    def convert(match: re.Match[str]) -> str:
        token = match.group(1)
        if token in {"", "+", "-"}:
            return token

        if mode == "z":
            # In generic impedance mode, units are scalar quantities that can
            # be used in formulas (e.g. j*omega*L).
            for unit in ("ohm", "H", "F"):
                try:
                    return repr(parse_value(token, unit))
                except (TypeError, ValueError):
                    continue
            return token

        if mode == "r":
            value = parse_value(token, "ohm")
            return repr(value)
        if mode == "l":
            value = parse_value(token, "H")
            return f"(j*omega*{value!r})"
        if mode == "c":
            value = parse_value(token, "F")
            return f"(1/(j*omega*{value!r}))"

        raise ValueError(f"Unknown impedance mode: {mode!r}")

    return _VALUE_WITH_SUFFIX_RE.sub(convert, expr)


def _passive_term_to_impedance(term: str, mode: str, omega: float | None) -> complex:
    if mode == "r":
        return complex(parse_value(term, "ohm"))
    if mode == "l":
        inductance = parse_value(term, "H")
        if omega is None:
            raise ValueError("Option --omega or --freq is required for impedance in --l mode.")
        return 1j * omega * inductance
    if mode == "c":
        capacitance = parse_value(term, "F")
        if omega is None:
            raise ValueError("Option --omega or --freq is required for impedance in --c mode.")
        return 1 / (1j * omega * capacitance)
    raise ValueError(f"Unknown mode: {mode!r}")


def _eval_passive_network(expr: str, mode: str, omega: float | None) -> complex:
    if re.search(r"(?<![eE])-", expr):
        raise ValueError(
            f"Subtraction is not supported in --{mode} mode. Use '+' and '||' only."
        )

    # In passive mode, expressions are component networks, not general formulas.
    if any(sym in expr.lower() for sym in ("j", "omega", "freq", "*", "/")):
        raise ValueError(
            f"General symbolic terms are not supported in --{mode} mode. "
            "Use component literals with '+' and '||'."
        )

    parallel_branches = _split_parallel(expr.strip())
    branch_values: list[complex] = []
    for branch in parallel_branches:
        terms = _split_top_level(branch, "+")
        value = 0j
        for term in terms:
            try:
                value += _passive_term_to_impedance(term, mode, omega)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid component term: {term!r}") from exc
        branch_values.append(value)

    if len(branch_values) == 1:
        return branch_values[0]

    inverse_sum = sum(1 / value for value in branch_values)
    if inverse_sum == 0:
        raise ValueError("Parallel expression leads to zero reciprocal sum.")
    return 1 / inverse_sum


def _eval_branch(expr: str, mode: str, omega: float | None) -> complex:
    normalized = expr.replace("Jomega", "jomega")
    # Treat jomega-prefixed literals as grouped terms, e.g. jomega4H -> (j*omega*4H).
    normalized = re.sub(
        r"jomega\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[A-Za-zµΩΩ]*)",
        r"(j*omega*\1)",
        normalized,
    )
    normalized = normalized.replace("jomega", "j*omega")
    replaced = _replace_literals(normalized, mode)

    locals_map: dict[str, object] = {
        "j": sp.I,
        "J": sp.I,
        "i": sp.I,
        "I": sp.I,
        "pi": sp.pi,
        "omega": omega if omega is not None else sp.Symbol("omega"),
    }

    transformations = standard_transformations + (
        convert_xor,
        implicit_multiplication_application,
        auto_symbol,
    )

    try:
        parsed = parse_expr(
            replaced,
            local_dict=locals_map,
            transformations=transformations,
            evaluate=True,
        )
    except Exception as exc:
        raise ValueError(f"Invalid expression branch: {expr!r}") from exc

    if mode in {"l", "c"} and omega is None:
        raise ValueError("Option --omega is required for inductive/capacitive impedance.")

    if mode == "z" and omega is None and "omega" in str(parsed):
        raise ValueError("Expression uses omega; provide --omega.")

    return _as_complex(parsed)


def equivalent_impedance(
    expression: str,
    *,
    mode: str = "z",
    omega: float | None = None,
) -> complex:
    expr = expression.strip()
    if not expr:
        raise ValueError("Expression must not be empty.")

    if mode in {"r", "c", "l"}:
        return _eval_passive_network(expr, mode, omega)

    branches = _split_parallel(expr)
    values = [_eval_branch(branch, mode, omega) for branch in branches]

    if len(values) == 1:
        return values[0]

    inverse_sum = sum(1 / value for value in values)
    if inverse_sum == 0:
        raise ValueError("Parallel expression leads to zero reciprocal sum.")
    return 1 / inverse_sum


def equivalent_resistance(expression: str) -> float:
    value = equivalent_impedance(expression, mode="r", omega=None)
    if abs(value.imag) > 1e-12:
        raise ValueError("Resistance result is not real.")
    return float(value.real)