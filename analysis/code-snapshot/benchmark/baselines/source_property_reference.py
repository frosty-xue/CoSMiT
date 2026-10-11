"""Source-only numerical definitions and domains; no candidate or target imports."""

from __future__ import annotations

import math
import random
from typing import Any


def scalar_reference(family: str, value: float) -> float:
    if family == "abs":
        return abs(value)
    if family == "neg":
        return -value
    if family == "square":
        return value * value
    if family == "sign":
        return float((value > 0) - (value < 0))
    if family == "reciprocal":
        return 1 / value
    if family == "sigmoid":
        return 1 / (1 + math.exp(-value))
    if family == "round":
        return float(round(value))
    return float(getattr(math, family)(value))


def valid_input(array: Any, domain: dict, np: Any) -> bool:
    low, high = domain["closed_interval"]
    return bool(
        str(array.dtype) in domain["dtypes"]
        and array.ndim <= domain["rank_max"]
        and array.size <= domain["elements_max"]
        and np.isfinite(array).all()
        and (array >= low).all()
        and (array <= high).all()
    )


def make_inputs(domain: dict, seed: int, np: Any) -> list[dict]:
    """64 inputs: two dtypes × four shapes × eight boundary/random cases."""
    low, high = domain["closed_interval"]
    boundaries = [low, high] + [
        v for v in [-4, -2, -1.5, -1, -0.5, -1e-6, 0, 1e-6, 0.5, 1, 1.5, 2, 4] if low <= v <= high
    ]
    rng = random.Random(seed)
    records = []
    for dtype in domain["dtypes"]:
        for shape in [[], [8], [2, 4], [1, 2, 2, 2]]:
            size = math.prod(shape)
            for index in range(8):
                values = (
                    [boundaries[(index * size + i) % len(boundaries)] for i in range(size)]
                    if index < 4
                    else [rng.uniform(low, high) for _ in range(size)]
                )
                array = np.asarray(values, dtype=dtype).reshape(shape)
                # Intervals are enforced on actual representable tensor values.
                lo = np.asarray(low, dtype=dtype)
                hi = np.asarray(high, dtype=dtype)
                if float(lo) < low:
                    lo = np.nextafter(lo, np.asarray(math.inf, dtype=dtype))
                if float(hi) > high:
                    hi = np.nextafter(hi, np.asarray(-math.inf, dtype=dtype))
                array = np.clip(array, lo, hi)
                if not valid_input(array, domain, np):
                    raise ValueError("Input generator left the registered domain")
                records.append(
                    {
                        "dtype": dtype,
                        "shape": shape,
                        "values": array.tolist(),
                        "strategy": "boundary" if index < 4 else "seeded-uniform",
                    }
                )
    return records
