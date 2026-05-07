import math


def ohm(v: float | None = None, i: float | None = None, r: float | None = None) -> dict[str, float]:
    given = [v is not None, i is not None, r is not None]

    if sum(given) != 2:
        raise ValueError("Exactly two of v, i, r must be provided.")

    if v is None:
        v = i * r
    elif i is None:
        i = v / r
    elif r is None:
        r = v / i

    p = v * i

    return {"v": v, "i": i, "r": r, "p": p}


def power(v: float | None = None, i: float | None = None, r: float | None = None) -> dict[str, float]:
    values = ohm(v=v, i=i, r=r)
    return {"p": values["p"], **values}


def rc(r: float, c: float, vin: float | None = None, v0: float = 0.0, t: float | None = None) -> dict[str, float | str]:
    tau = r * c
    fc = 1 / (2 * math.pi * tau)

    result = {
        "tau": tau,
        "fc": fc,
        "formula": "vC(t) = Vf + (V0 - Vf) * exp(-t / tau)",
    }

    if vin is not None:
        result["vf"] = vin

        if t is not None:
            result["vt"] = vin + (v0 - vin) * math.exp(-t / tau)

    return result


def rl(r: float, l: float, vin: float | None = None, i0: float = 0.0, t: float | None = None) -> dict[str, float | str]:
    tau = l / r
    fc = r / (2 * math.pi * l)

    result = {
        "tau": tau,
        "fc": fc,
        "formula": "i(t) = If + (I0 - If) * exp(-t / tau)",
    }

    if vin is not None:
        i_final = vin / r
        result["if"] = i_final

        if t is not None:
            result["it"] = i_final + (i0 - i_final) * math.exp(-t / tau)

    return result


def voltage_divider(vin: float, r1: float, r2: float) -> dict[str, float]:
    v1 = vin * r1 / (r1 + r2)
    v2 = vin * r2 / (r1 + r2)

    return {
        "vin": vin,
        "r1": r1,
        "r2": r2,
        "v1": v1,
        "v2": v2,
        "ratio": v2 / vin,
    }


def current_divider(iin: float, r1: float, r2: float) -> dict[str, float]:
    i1 = iin * r2 / (r1 + r2)
    i2 = iin * r1 / (r1 + r2)

    return {
        "iin": iin,
        "r1": r1,
        "r2": r2,
        "i1": i1,
        "i2": i2,
        "ratio": i2 / iin,
    }
