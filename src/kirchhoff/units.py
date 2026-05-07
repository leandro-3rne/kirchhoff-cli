import re

PREFIXES = {
    "T": 1e12,
    "G": 1e9,
    "M": 1e6,
    "k": 1e3,
    "": 1.0,
    "m": 1e-3,
    "u": 1e-6,
    "µ": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
}

UNIT_ALIASES = {
    "": "",
    "ohm": "ohm",
    "Ohm": "ohm",
    "Ohms": "ohm",
    "OHM": "ohm",
    "OHMS": "ohm",
    "ohms": "ohm",
    "o": "ohm",
    "O": "ohm",
    "Ω": "ohm",
    "Ω": "ohm",
    "a": "A",
    "amp": "A",
    "amps": "A",
    "Amp": "A",
    "Amps": "A",
    "AMPS": "A",
    "AMP": "A",
    "v": "V",
    "volt": "V",
    "volts": "V",
    "Volt": "V",
    "VOLT": "V",
    "VOLTS": "V",
    "Volts": "V",
    "f": "F",
    "farad": "F",
    "farads": "F",
    "Farad": "F",
    "Farads": "F",
    "FARAD": "F",
    "FARADS": "F",
    "fahrad": "F",
    "fahrads": "F",
    "Fahrad": "F",
    "Fahrads": "F",
    "FAHRAD": "F",
    "FAHRADS": "F",
    "h": "H",
    "henry": "H",
    "henrys": "H",
    "Henry": "H",
    "Henrys": "H",
    "HENRY": "H",
    "HENRYS": "H",
    "hanry": "H",
    "hanrys": "H",
    "Hanry": "H",
    "Hanrys": "H",
    "HANRY": "H",
    "HANRYS": "H",
    "s": "s",
    "sec": "s",
    "secs": "s",
    "second": "s",
    "seconds": "s",
    "SEC": "s",
    "SECS": "s",
    "SECOND": "s",
    "SECONDS": "s",
}

VALUE_RE = re.compile(
    r"""
    ^\s*
    (?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)
    \s*
    (?P<suffix>[A-Za-zµΩΩ]*)
    \s*$
    """,
    re.VERBOSE,
)


def parse_value(value: str, expected_unit: str | None = None) -> float:
    """
    Parse values like:
      1k, 4.7k, 10mA, 100nF, 6e-3ohm, 2Mohm, 1.5uF, 3µF, 2T

    expected_unit examples:
      "ohm", "V", "A", "F", "H"

    If expected_unit is given, incompatible units raise ValueError.
    """

    if not isinstance(value, str):
        raise TypeError("value must be a string")

    match = VALUE_RE.match(value)
    if not match:
        raise ValueError(f"Invalid value syntax: {value!r}")

    number = float(match.group("number"))
    suffix = match.group("suffix")

    prefix, unit = split_prefix_unit(suffix)
    factor = PREFIXES[prefix]

    normalized_unit = normalize_unit(unit)

    if expected_unit is not None:
        expected_unit = normalize_unit(expected_unit)
        if normalized_unit not in ("", expected_unit):
            raise ValueError(
                f"Expected unit {expected_unit!r}, got {normalized_unit!r} in {value!r}"
            )

    return number * factor


def split_prefix_unit(suffix: str) -> tuple[str, str]:
    """
    Split suffix into SI prefix and unit.

    Examples:
      k       -> ("k", "")
      kohm    -> ("k", "ohm")
      mA      -> ("m", "A")
      uF      -> ("u", "F")
      µF      -> ("µ", "F")
      ohm     -> ("", "ohm")
      V       -> ("", "V")
    """

    if suffix == "":
        return "", ""

    # Full unit without prefix
    try:
        if normalize_unit(suffix) != "":
            return "", suffix
    except ValueError:
        pass

    # Prefix + unit
    first = suffix[0]
    rest = suffix[1:]

    if first in PREFIXES:
        if rest == "":
            return first, ""
        try:
            normalize_unit(rest)
            return first, rest
        except ValueError:
            pass

    raise ValueError(f"Unknown prefix or unit suffix: {suffix!r}")


def normalize_unit(unit: str) -> str:
    unit = unit.strip()

    if unit == "":
        return ""

    # Preserve case-sensitive SI units first
    if unit in {"A", "V", "F", "H"}:
        return unit

    lower = unit.lower()

    if lower in UNIT_ALIASES:
        return UNIT_ALIASES[lower]

    if unit in UNIT_ALIASES:
        return UNIT_ALIASES[unit]

    raise ValueError(f"Unknown unit: {unit!r}")


def format_si(value: float, unit: str = "", precision: int = 4) -> str:
    """
    Format a number with a suitable SI prefix.
    Example:
      0.001 -> 1 m
      4700  -> 4.7 k
    """

    if value == 0:
        return f"0 {unit}".strip()

    abs_value = abs(value)

    prefixes = [
        ("T", 1e12),
        ("G", 1e9),
        ("M", 1e6),
        ("k", 1e3),
        ("", 1.0),
        ("m", 1e-3),
        ("µ", 1e-6),
        ("n", 1e-9),
        ("p", 1e-12),
    ]

    for prefix, factor in prefixes:
        scaled = abs_value / factor
        if 1 <= scaled < 1000:
            signed_scaled = value / factor
            return f"{signed_scaled:.{precision}g} {prefix}{unit}".strip()

    return f"{value:.{precision}e} {unit}".strip()