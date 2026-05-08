import sys
import cmath
import math
import re
from typing import Optional

import typer
import sympy as sp
from rich.console import Console
from rich.table import Table

from kirchhoff.circuits import current_divider, voltage_divider
from kirchhoff.circuits import ohm as solve_ohm
from kirchhoff.circuits import power as solve_power
from kirchhoff.circuits import rc as solve_rc
from kirchhoff.circuits import rl as solve_rl
from kirchhoff.formatting import print_kv, print_title
from kirchhoff.resistance import equivalent_impedance
from kirchhoff.symbolic import taylor_series, fourier_series
from kirchhoff.units import format_si, parse_value


def _configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


_configure_output_encoding()

app = typer.Typer(help="Electrical engineering command-line toolkit.")
console = Console()

PRIMARY = "#f5c71a"
SECONDARY = "#d4a900"
ACCENT = "#8b5cf6"
DIM = "#8a8a8a"

BANNER = r"""
██╗  ██╗██╗██████╗  ██████╗██╗  ██╗██╗  ██╗ ██████╗ ███████╗███████╗
██║ ██╔╝██║██╔══██╗██╔════╝██║  ██║██║  ██║██╔═══██╗██╔════╝██╔════╝
█████╔╝ ██║██████╔╝██║     ███████║███████║██║   ██║█████╗  █████╗
██╔═██╗ ██║██╔══██╗██║     ██╔══██║██╔══██║██║   ██║██╔══╝  ██╔══╝
██║  ██╗██║██║  ██║╚██████╗██║  ██║██║  ██║╚██████╔╝██║     ██║
╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝
"""


def print_banner() -> None:
    console.print()

    lines = BANNER.strip("\n").splitlines()
    for i, line in enumerate(lines):
        color = PRIMARY if i < 3 else SECONDARY
        console.print(f"[bold {color}]{line}[/bold {color}]")
    console.print(f"[bold {PRIMARY}]Electrical Engineering CLI Toolkit")
    console.print(
        f"[bold {SECONDARY}]Circuits • Transient Analysis • Taylor Series • Fourier Series[/bold {SECONDARY}]"
    )
    console.print(
        f"[{DIM}]Run[/ {DIM}] [bold {ACCENT}]khoff --help[/bold {ACCENT}] "
        f"[{DIM}]or[/ {DIM}] [bold {ACCENT}]khoff <command> --help[/bold {ACCENT}]"
    )
    console.print()


def print_commands() -> None:
    table = Table(
        show_header=True,
        header_style=f"bold {PRIMARY}",
        border_style=ACCENT,
        show_lines=False,
    )

    table.add_column("Command", style=f"bold {ACCENT}", no_wrap=True)
    table.add_column("Description", style=SECONDARY)

    table.add_row("z", "Calculate equivalent impedance from a series/parallel expression")
    table.add_row("ohm", "Solve Ohm's law. Provide exactly two of V, I, and R")
    table.add_row("pow", "Compute power P and derived V, I, R values from two inputs")
    table.add_row("div", "Analyze voltage and current divider circuits")
    table.add_row("rc", "Analyze an RC circuit: tau, cutoff frequency, and optional vC(t)")
    table.add_row("rl", "Analyze an RL circuit: tau, cutoff frequency, and optional i(t)")
    table.add_row("ts", "Compute a Taylor polynomial and optional numeric evaluation")
    table.add_row("fs", "Compute a truncated Fourier series and optional numeric evaluation")

    console.print(table)
    console.print()


def _parse_option_value(value: str, expected_unit: str, option_name: str) -> float:
    try:
        return parse_value(value, expected_unit)
    except (TypeError, ValueError) as exc:
        raise typer.BadParameter(f"Invalid value for {option_name}: {exc}") from exc


def _format_taylor_polynomial(polynomial: object, variable: str) -> str:
    """
    Render Taylor polynomial in ascending powers where possible.
    Falls back to default string if not a univariate polynomial form.
    """
    x = sp.Symbol(variable)
    try:
        poly = sp.Poly(sp.expand(polynomial), x)
    except Exception:
        return str(polynomial)

    pieces: list[str] = []
    for power in sorted(range(poly.degree() + 1)):
        coeff = sp.simplify(poly.nth(power))
        if coeff == 0:
            continue
        term = coeff if power == 0 else coeff * x**power
        pieces.append(str(sp.simplify(term)))

    if not pieces:
        return "0"

    rendered = pieces[0]
    for piece in pieces[1:]:
        if piece.startswith("-"):
            rendered += f" - {piece[1:]}"
        else:
            rendered += f" + {piece}"
    return rendered


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        print_banner()
        print_commands()


@app.command()
def z(
    expression_parts: list[str] = typer.Argument(
        None,
        help='Impedance expression. Use quotes, e.g. "(5 + 8j) || (6 - 1/8j)".',
    ),
    omega: Optional[str] = typer.Option(
        None,
        "--omega",
        help="Angular frequency ω in rad/s (numeric only, e.g. 376.99).",
    ),
    freq: Optional[str] = typer.Option(
        None,
        "--freq",
        help="Frequency f in Hz (e.g. 6, 6Hz, 78kHz).",
    ),
    r: Optional[str] = typer.Option(
        None,
        "--r",
        help='Resistance network expression, e.g. "5 || 3 + 2".',
    ),
    c: Optional[str] = typer.Option(
        None,
        "--c",
        help='Capacitor network expression, e.g. "5 + 3f" (uses + and || only).',
    ),
    l: Optional[str] = typer.Option(
        None,
        "--l",
        help='Inductor network expression, e.g. "5h || 8kH" (uses + and || only).',
    ),
) -> None:
    """Calculate equivalent impedance from a series/parallel expression"""
    provided_modes = [r is not None, c is not None, l is not None]
    if omega is not None and freq is not None:
        raise typer.BadParameter("Use only one of --omega or --freq.")

    if sum(provided_modes) > 1:
        raise typer.BadParameter("Use at most one of --r, --c, --l.")

    if sum(provided_modes) == 1 and expression_parts:
        if r is not None:
            option_name = "--r"
            example = 'khoff z --r "5 || 3 + 2"'
        elif c is not None:
            option_name = "--c"
            example = 'khoff z --c "5 + 3f"'
        else:
            option_name = "--l"
            example = 'khoff z --l "5h || 8kH"'
        raise typer.BadParameter(
            f"Wrap the full expression for {option_name} in quotes, e.g. {example}."
        )

    if sum(provided_modes) == 0:
        if not expression_parts or len(expression_parts) != 1:
            raise typer.BadParameter(
                'Wrap the full expression in quotes, e.g. "(5 + 8j) || (6 - 1/8j)".'
            )
        mode = "z"
        expression = expression_parts[0].strip()
    elif r is not None:
        mode = "r"
        expression = r.strip()
    elif c is not None:
        mode = "c"
        expression = c.strip()
    else:
        mode = "l"
        expression = l.strip()

    omega_value: float | None = None
    freq_value: float | None = None
    given_freq = False

    if omega is not None:
        omega_text = omega.strip()
        try:
            if re.search(r"[A-Za-zµΩΩ]", omega_text):
                raise ValueError("omega must be in rad/s and must not include a unit suffix")
            omega_value = parse_value(omega_text)
            freq_value = omega_value / (2 * math.pi)
        except (TypeError, ValueError) as exc:
            raise typer.BadParameter(f"Invalid value for --omega: {exc}") from exc

    if freq is not None:
        freq_text = freq.strip()
        try:
            freq_value = parse_value(freq_text, "Hz")
            omega_value = 2 * math.pi * freq_value
            given_freq = True
        except (TypeError, ValueError) as exc:
            raise typer.BadParameter(f"Invalid value for --freq: {exc}") from exc

    if not expression:
        raise typer.BadParameter(
            "Invalid expression: expression must not be empty."
        )

    output_mode = "impedance"
    eval_omega = omega_value
    if mode in {"c", "l"} and eval_omega is None:
        # Compute equivalent C/L without a supplied frequency.
        eval_omega = 1.0
        output_mode = mode

    try:
        z_eq = equivalent_impedance(expression, mode=mode, omega=eval_omega)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid expression: {exc}") from exc

    if freq_value is None and omega_value is not None:
        freq_value = omega_value / (2 * math.pi)

    z_mag = abs(z_eq)
    z_phase_deg = math.degrees(cmath.phase(z_eq))
    z_repr = f"{z_eq.real:.6g} {'+' if z_eq.imag >= 0 else '-'} {abs(z_eq.imag):.6g}j"

    print_title(console, "Impedance Analysis", PRIMARY)
    print_kv(console, "Expression", expression)
    if given_freq:
        print_kv(console, "f", f"{freq_value:.6g} Hz")
        print_kv(console, "ω", f"{omega_value:.6g} rad/s")
    elif omega_value is not None:
        print_kv(console, "ω", f"{omega_value:.6g} rad/s")
        print_kv(console, "f", f"{freq_value:.6g} Hz")
    else:
        print_kv(console, "ω", "not provided")
        print_kv(console, "f", "not provided")

    if output_mode == "c":
        if abs(z_eq.imag) < 1e-15:
            raise typer.BadParameter("Invalid expression: equivalent capacitance is undefined.")
        ceq = -1.0 / z_eq.imag
        print_kv(console, "Ceq", format_si(ceq, "F"), bold_value=True)
        return

    if output_mode == "l":
        leq = z_eq.imag
        print_kv(console, "Leq", format_si(leq, "H"), bold_value=True)
        return

    print_kv(console, "Zeq", z_repr, bold_value=True)
    print_kv(console, "|Z|", f"{z_mag:.6g}")
    print_kv(console, "Phase", f"{z_phase_deg:.6g} deg")


@app.command()
def ohm(
    v: Optional[str] = typer.Option(None, "--v", help="Voltage V (e.g. 5, 3.3V)"),
    i: Optional[str] = typer.Option(None, "--i", help="Current I (e.g. 20mA)"),
    r: Optional[str] = typer.Option(None, "--r", help="Resistance R (e.g. 220, 4.7k)"),
) -> None:
    """Solve Ohm's law. Provide exactly two of V, I, and R"""
    try:
        result = solve_ohm(
            v=_parse_option_value(v, "V", "--v") if v else None,
            i=_parse_option_value(i, "A", "--i") if i else None,
            r=_parse_option_value(r, "ohm", "--r") if r else None,
        )
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid inputs: {exc}") from exc

    print_title(console, "Ohm's Law", PRIMARY)
    print_kv(console, "V", format_si(result["v"], "V"), bold_value=True)
    print_kv(console, "I", format_si(result["i"], "A"), bold_value=True)
    print_kv(console, "R", format_si(result["r"], "Ω"), bold_value=True)
    print_kv(console, "P", format_si(result["p"], "W"), bold_value=True)


@app.command("pow")
def power(
    v: Optional[str] = typer.Option(None, "--v", help="Voltage V (e.g. 5, 3.3V)"),
    i: Optional[str] = typer.Option(None, "--i", help="Current I (e.g. 20mA)"),
    r: Optional[str] = typer.Option(None, "--r", help="Resistance R (e.g. 220, 4.7k)"),
) -> None:
    """Compute power P and derived V, I, R values from two inputs"""
    try:
        result = solve_power(
            v=_parse_option_value(v, "V", "--v") if v else None,
            i=_parse_option_value(i, "A", "--i") if i else None,
            r=_parse_option_value(r, "ohm", "--r") if r else None,
        )
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid inputs: {exc}") from exc

    print_title(console, "Power", PRIMARY)
    print_kv(console, "P", format_si(result["p"], "W"), bold_value=True)
    print_kv(console, "V", format_si(result["v"], "V"))
    print_kv(console, "I", format_si(result["i"], "A"))
    print_kv(console, "R", format_si(result["r"], "Ω"))


@app.command()
def div(
    mode: str = typer.Argument(..., help="Divider mode: 'v' for voltage, 'i' for current"),
    r1: str = typer.Option(..., "--r1", help="Resistor R1 (e.g. 10k)"),
    r2: str = typer.Option(..., "--r2", help="Resistor R2 (e.g. 4.7k)"),
    vin: Optional[str] = typer.Option(
        None,
        "--vin",
        help="Input voltage Vin for mode 'v' (e.g. 5V)",
    ),
    iin: Optional[str] = typer.Option(
        None,
        "--iin",
        help="Input current Iin for mode 'i' (e.g. 10mA)",
    ),
) -> None:
    """Analyze voltage and current divider circuits"""
    try:
        r1_value = _parse_option_value(r1, "ohm", "--r1")
        r2_value = _parse_option_value(r2, "ohm", "--r2")
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid inputs: {exc}") from exc

    if mode == "v":
        if vin is None:
            raise typer.BadParameter("Invalid value for --vin: required when mode is 'v'")
        try:
            vin_value = _parse_option_value(vin, "V", "--vin")
            result = voltage_divider(vin=vin_value, r1=r1_value, r2=r2_value)
        except ValueError as exc:
            raise typer.BadParameter(f"Invalid inputs: {exc}") from exc

        print_title(console, "Voltage Divider", PRIMARY)
        print_kv(console, "Vin  ", format_si(result["vin"], "V"))
        print_kv(console, "V1   ", format_si(result["v1"], "V"), bold_value=True)
        print_kv(console, "V2   ", format_si(result["v2"], "V"), bold_value=True)
        print_kv(console, "Ratio", f"{result['ratio']:.4f} (V2/Vin)")
        return

    if mode == "i":
        if iin is None:
            raise typer.BadParameter("Invalid value for --iin: required when mode is 'i'")
        try:
            iin_value = _parse_option_value(iin, "A", "--iin")
            result = current_divider(iin=iin_value, r1=r1_value, r2=r2_value)
        except ValueError as exc:
            raise typer.BadParameter(f"Invalid inputs: {exc}") from exc

        print_title(console, "Current Divider", PRIMARY)
        print_kv(console, "Iin", format_si(result["iin"], "A"))
        print_kv(console, "I1 ", format_si(result["i1"], "A"), bold_value=True)
        print_kv(console, "I2 ", format_si(result["i2"], "A"), bold_value=True)
        print_kv(console, "Ratio", f"{result['ratio']:.4f} (I2/Iin)")
        return

    raise typer.BadParameter("Invalid value for mode: must be 'v' or 'i'")


@app.command()
def rc(
    r: str = typer.Option(..., "--r", help="Resistance R (e.g. 10k)"),
    c: str = typer.Option(..., "--c", help="Capacitance C (e.g. 100nF)"),
    vin: Optional[str] = typer.Option(None, "--vin", help="Final/input voltage Vf (e.g. 5V)"),
    v0: str = typer.Option("0V", "--v0", help="Initial capacitor voltage V0 (default: 0V)"),
    t: Optional[str] = typer.Option(None, "--t", help="Evaluation time t (e.g. 2ms)"),
) -> None:
    """Analyze an RC circuit: tau, cutoff frequency, and optional vC(t)"""
    try:
        r_value = _parse_option_value(r, "ohm", "--r")
        c_value = _parse_option_value(c, "F", "--c")
        vin_value = _parse_option_value(vin, "V", "--vin") if vin else None
        v0_value = _parse_option_value(v0, "V", "--v0")
        t_value = _parse_option_value(t, "s", "--t") if t else None
        result = solve_rc(r=r_value, c=c_value, vin=vin_value, v0=v0_value, t=t_value)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid inputs: {exc}") from exc

    print_title(console, "RC Transient Analysis", PRIMARY)
    print_kv(console, "τ ", format_si(result["tau"], "s"), bold_value=True)
    print_kv(console, "fc", format_si(result["fc"], "Hz"), bold_value=True)
    if vin_value is not None:
        print_kv(console, "Vf", format_si(result["vf"], "V"))
    console.print("vC(t) = Vf + (V0 - Vf) · exp(-t / τ)")

    if "vt" in result:
        print_kv(
            console,
            f"vC({format_si(t_value, 's')})",
            format_si(result["vt"], "V"),
            bold_value=True,
        )


@app.command()
def rl(
    r: str = typer.Option(..., "--r", help="Resistance R (e.g. 100)"),
    l: str = typer.Option(..., "--l", help="Inductance L (e.g. 10mH)"),
    vin: Optional[str] = typer.Option(None, "--vin", help="Input voltage Vin (e.g. 5V)"),
    i0: str = typer.Option("0A", "--i0", help="Initial inductor current I0 (default: 0A)"),
    t: Optional[str] = typer.Option(None, "--t", help="Evaluation time t (e.g. 1ms)"),
) -> None:
    """Analyze an RL circuit: tau, cutoff frequency, and optional i(t)"""
    try:
        r_value = _parse_option_value(r, "ohm", "--r")
        l_value = _parse_option_value(l, "H", "--l")
        vin_value = _parse_option_value(vin, "V", "--vin") if vin else None
        i0_value = _parse_option_value(i0, "A", "--i0")
        t_value = _parse_option_value(t, "s", "--t") if t else None
        result = solve_rl(r=r_value, l=l_value, vin=vin_value, i0=i0_value, t=t_value)
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid inputs: {exc}") from exc

    print_title(console, "RL Transient Analysis", PRIMARY)
    print_kv(console, "τ ", format_si(result["tau"], "s"), bold_value=True)
    print_kv(console, "fc", format_si(result["fc"], "Hz"), bold_value=True)
    if vin_value is not None:
        print_kv(console, "If", format_si(result["if"], "A"))
    console.print("i(t) = If + (I0 - If) · exp(-t / τ)")

    if "it" in result:
        print_kv(
            console,
            f"i({format_si(t_value, 's')})",
            format_si(result["it"], "A"),
            bold_value=True,
        )


@app.command()
def ts(
    expression_parts: list[str] = typer.Argument(
        ...,
        help=(
            'Expression f(x). Use quotes, e.g. "exp(x) + x^3". '
            "Symbols other than --var are treated as constants."
        ),
    ),
    variable: str = typer.Option(
        "x",
        "--var",
        help="Series variable. Other symbols are treated as constants.",
    ),
    around: str = typer.Option("0", "--around", help="Expansion point a."),
    order: int = typer.Option(5, "--order", help="Taylor order n (>= 0)"),
    value: Optional[str] = typer.Option(None, "--value", help="Evaluation point (optional)"),
) -> None:
    """Compute a Taylor polynomial and optional numeric evaluation"""
    if len(expression_parts) != 1:
        raise typer.BadParameter(
            'Wrap the full expression in quotes, e.g. "exp(x) + x^3".'
        )
    if order < 0:
        raise typer.BadParameter("Invalid value for --order: must be >= 0")

    expression = expression_parts[0].strip()
    try:
        result = taylor_series(
            expression=expression,
            variable=variable,
            around=around,
            order=order,
            value=value,
        )
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid expression or parameters: {exc}") from exc
    console.print(f"[bold {PRIMARY}]Taylor Series[/bold {PRIMARY}]")
    console.print(f"f({result['variable']}) = {result['expression']}")
    console.print(f"Around a   = {result['around']}")
    console.print(f"Order      = {result['order']}")
    poly_text = _format_taylor_polynomial(result["polynomial"], variable)
    console.print(f"Polynomial = [bold]{poly_text}[/bold]")
    if value is not None:
        console.print(f"P({value}) = {result['approximation']}")
        console.print(f"f({value}) = {result['true_value']}")
        console.print(f"Error      = {result['error']}")


@app.command()
def fs(
    expression_parts: list[str] = typer.Argument(
        ...,
        help=(
            'Expression f(x). Use quotes, e.g. "sin(x) + x^2". '
            "Symbols other than --var are treated as constants."
        ),
    ),
    variable: str = typer.Option(
        "x",
        "--var",
        help="Series variable. Other symbols are treated as constants.",
    ),
    period: str = typer.Option("2*pi", "--period", help="Function period T."),
    order: int = typer.Option(5, "--order", help="Number of harmonics/terms (>= 0)"),
    value: Optional[str] = typer.Option(None, "--value", help="Evaluation point (optional)"),
) -> None:
    """Compute a truncated Fourier series and optional numeric evaluation"""
    if len(expression_parts) != 1:
        raise typer.BadParameter(
            'Wrap the full expression in quotes, e.g. "sin(x) + x^2".'
        )
    if order < 0:
        raise typer.BadParameter("Invalid value for --order: must be >= 0")

    expression = expression_parts[0].strip()
    try:
        result = fourier_series(
            expression=expression,
            variable=variable,
            period=period,
            order=order,
            value=value,
        )
    except ValueError as exc:
        raise typer.BadParameter(f"Invalid expression or parameters: {exc}") from exc
    console.print(f"[bold {PRIMARY}]Fourier Series[/bold {PRIMARY}]")
    console.print(f"f({result['variable']}) = {result['expression']}")
    console.print(f"Period T   = {result['period']}")
    console.print(f"Order      = {result['order']}")
    console.print(f"PartialSum = [bold]{result['polynomial']}[/bold]")
    if value is not None:
        console.print(f"S({value}) = {result['approximation']}")
        console.print(f"f({value}) = {result['true_value']}")
        console.print(f"Error      = {result['error']}")


if __name__ == "__main__":
    app()
