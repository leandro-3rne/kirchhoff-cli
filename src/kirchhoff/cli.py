import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

PRIMARY = "#f5c71a"      # warm yellow
SECONDARY = "#d4a900"    # darker gold
ACCENT = "#8b5cf6"       # subtle violet
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
    console.print(
    f"[bold {PRIMARY}]Electrical Engineering CLI Toolkit"
    )
    console.print(
        f"[bold {SECONDARY}]Circuit Analysis • Signals • Fourier • Symbolics[/bold {SECONDARY}]"
    )
    console.print(f"[{DIM}]Run[/ {DIM}] [bold {ACCENT}]khoff --help[/bold {ACCENT}] [{DIM}]or[/ {DIM}] [bold {ACCENT}]khoff <command> --help[/bold {ACCENT}]")
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

    table.add_row("r", "Resistance analysis")
    table.add_row("ohm", "Ohm's law solver")
    table.add_row("power", "Power calculations")
    table.add_row("div", "Divider analysis")
    table.add_row("rc", "RC transient analysis")
    table.add_row("rl", "RL transient analysis")
    table.add_row("fs", "Fourier series expansion")
    table.add_row("ts", "Taylor series expansion")

    console.print(table)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        print_banner()
        print_commands()


@app.command()
def r():
    """Equivalent resistance."""
    console.print(f"[{DIM}]Not implemented yet.[/{DIM}]")


@app.command()
def ohm():
    """Ohm's law."""
    console.print(f"[{DIM}]Not implemented yet.[/{DIM}]")


@app.command()
def power():
    """Electrical power."""
    console.print(f"[{DIM}]Not implemented yet.[/{DIM}]")


@app.command()
def div():
    """Voltage and current divider."""
    console.print(f"[{DIM}]Not implemented yet.[/{DIM}]")


@app.command()
def rc():
    """RC time constant and cutoff frequency."""
    console.print(f"[{DIM}]Not implemented yet.[/{DIM}]")


@app.command()
def rl():
    """RL time constant and cutoff frequency."""
    console.print(f"[{DIM}]Not implemented yet.[/{DIM}]")


@app.command()
def fs():
    """Fourier series."""
    console.print(f"[{DIM}]Not implemented yet.[/{DIM}]")


@app.command()
def ts():
    """Taylor series."""
    console.print(f"[{DIM}]Not implemented yet.[/{DIM}]")


if __name__ == "__main__":
    app()