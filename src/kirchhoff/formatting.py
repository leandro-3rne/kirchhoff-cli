"""Formatting helpers for CLI output."""

from rich.console import Console


def print_title(console: Console, title: str, color: str) -> None:
    """Print a colored section title."""
    console.print(f"[bold {color}]{title}[/bold {color}]")


def print_kv(console: Console, label: str, value: str, *, bold_value: bool = False) -> None:
    """Print a `Label = Value` line with optional bold value."""
    rendered_value = f"[bold]{value}[/bold]" if bold_value else value
    console.print(f"{label} = {rendered_value}")
