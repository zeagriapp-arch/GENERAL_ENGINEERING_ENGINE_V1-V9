"""
Regression testing (sección 27): "Si un cambio rompe resultados
previamente validados: REGRESSION DETECTED. No ocultar cambios
numéricos." Guarda el último resultado conocido-bueno de cada benchmark
y compara contra el nuevo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RegressionCheckResult:
    regression_detected: bool
    benchmark_id: str
    previous: dict[str, float] | None
    new: dict[str, float]
    difference: dict[str, float]
    is_first_run: bool = False


class RegressionStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            self.path.write_text("{}")

    def _load(self) -> dict:
        return json.loads(self.path.read_text())

    def _save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2))

    def check(self, benchmark_id: str, new_values: dict[str, float], *, threshold: float = 1e-6) -> RegressionCheckResult:
        data = self._load()
        previous = data.get(benchmark_id)

        if previous is None:
            return RegressionCheckResult(
                regression_detected=False,
                benchmark_id=benchmark_id,
                previous=None,
                new=new_values,
                difference={},
                is_first_run=True,
            )

        difference = {}
        regression = False
        for key, new_val in new_values.items():
            old_val = previous.get(key)
            if old_val is None:
                continue
            denom = abs(old_val) if old_val != 0 else 1.0
            diff = abs(new_val - old_val) / denom
            difference[key] = diff
            if diff > threshold:
                regression = True

        return RegressionCheckResult(
            regression_detected=regression,
            benchmark_id=benchmark_id,
            previous=previous,
            new=new_values,
            difference=difference,
        )

    def record(self, benchmark_id: str, values: dict[str, float]) -> None:
        data = self._load()
        data[benchmark_id] = values
        self._save(data)
