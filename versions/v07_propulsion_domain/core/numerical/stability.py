"""
Detección de inestabilidad numérica (sección 16). "No devolver un
resultado numérico como válido si el solver reporta inestabilidad."
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class StabilityCheck:
    stable: bool
    notes: list[str] = field(default_factory=list)


def check_array_stability(values: np.ndarray, *, name: str = "values") -> StabilityCheck:
    notes: list[str] = []
    if np.isnan(values).any():
        notes.append(f"{name} contiene NaN.")
    if np.isinf(values).any():
        notes.append(f"{name} contiene Inf.")
    finite = values[np.isfinite(values)]
    if finite.size > 0 and np.max(np.abs(finite)) > 1e300:
        notes.append(f"{name} tiene magnitudes que sugieren overflow (>1e300).")
    return StabilityCheck(stable=len(notes) == 0, notes=notes)
