"""Frozen scalar reference algorithms and inputs for six reserved operation families."""

from __future__ import annotations

import itertools
import math
from typing import Any


def reference(family: str, matrix: Any, other: Any, axis: int, keepdim: bool, np: Any) -> Any:
    values = matrix.astype("float64")
    rows, columns = values.shape
    if family == "matmul":
        return np.asarray(
            [
                [
                    sum(float(values[i, k]) * float(other[k, j]) for k in range(columns))
                    for j in range(other.shape[1])
                ]
                for i in range(rows)
            ]
        )
    if family == "det":
        terms = []
        for permutation in itertools.permutations(range(rows)):
            inversions = sum(
                permutation[i] > permutation[j] for i in range(rows) for j in range(i + 1, rows)
            )
            terms.append(
                (-1) ** inversions
                * math.prod(float(values[i, permutation[i]]) for i in range(rows))
            )
        return np.asarray(math.fsum(terms))
    if family == "trace":
        return np.asarray(sum(float(values[i, i]) for i in range(min(rows, columns))))
    normalized_axis = axis % 2
    moved = np.moveaxis(values, normalized_axis, -1)
    if family == "prod":
        result = np.asarray([math.prod(float(v) for v in row) for row in moved])
        return np.expand_dims(result, normalized_axis) if keepdim else result
    if family in {"cumsum", "cumprod"}:
        operation = sum if family == "cumsum" else math.prod
        result = np.asarray(
            [[operation(float(v) for v in row[: i + 1]) for i in range(len(row))] for row in moved]
        )
        return np.moveaxis(result, -1, normalized_axis)
    raise ValueError("Unregistered unseen family")


def valid_domain(family: str, matrix: Any, other: Any, axis: int, np: Any) -> bool:
    def bounded(value: Any) -> bool:
        return bool(
            value.ndim == 2
            and str(value.dtype) in {"float32", "float64"}
            and value.size <= 16
            and min(value.shape) >= 1
            and max(value.shape) <= 4
            and np.isfinite(value).all()
            and (value == np.floor(value)).all()
        )

    if not bounded(matrix) or type(axis) is not int or axis not in {0, 1, -1, -2}:
        return False
    if family == "det":
        if matrix.shape[0] != matrix.shape[1]:
            return False
        for i, row in enumerate(matrix):
            others = [float(v) for j, v in enumerate(row) if j != i]
            if (
                any(abs(v) > 3 for v in others)
                or not 0 < float(row[i]) <= 13
                or float(row[i]) <= sum(abs(v) for v in others)
            ):
                return False
    elif not (np.abs(matrix) <= 3).all():
        return False
    if family == "matmul":
        return (
            bounded(other)
            and matrix.dtype == other.dtype
            and matrix.shape[1] == other.shape[0]
            and bool((np.abs(other) <= 3).all())
        )
    return family in {"prod", "det", "trace", "cumsum", "cumprod"}


def generate(protocol: dict, family: str, np: Any) -> list[dict]:
    design = protocol["input_design"]
    rng = np.random.default_rng(design["seed"])
    shapes = (
        design["matmul_shapes"]
        if family == "matmul"
        else design["det_shapes"]
        if family == "det"
        else design["matrix_shapes"]
    )
    records = []

    def values(shape: list[int], scenario: int, dtype: str) -> Any:
        if scenario == 0:
            return np.zeros(shape, dtype=dtype)
        if scenario == 1:
            return np.ones(shape, dtype=dtype)
        if scenario == 2:
            return np.asarray(
                [3 if i % 2 else -3 for i in range(math.prod(shape))], dtype=dtype
            ).reshape(shape)
        if scenario == 3:
            return (np.arange(math.prod(shape)).reshape(shape) % 7 - 3).astype(dtype)
        return rng.integers(-3, 4, size=shape).astype(dtype)

    for dtype in design["dtype"]:
        for shape in shapes:
            for scenario in range(8):
                matrix = values(shape[0] if family == "matmul" else shape, scenario, dtype)
                other = values(shape[1], scenario, dtype) if family == "matmul" else None
                if family == "det":
                    for i in range(len(matrix)):
                        matrix[i, i] = (
                            abs(float(matrix[i, i]))
                            + sum(abs(float(matrix[i, j])) for j in range(len(matrix)) if j != i)
                            + 1
                        )
                axis = [0, 1, -1, -2][scenario % 4]
                if not valid_domain(family, matrix, other, axis, np):
                    raise ValueError("Generated input violates frozen source domain")
                records.append(
                    {
                        "dtype": dtype,
                        "matrix": matrix.tolist(),
                        "other": other.tolist() if other is not None else None,
                        "axis": axis,
                        "keepdim": bool(scenario % 2),
                        "scenario": scenario,
                    }
                )
    return records
