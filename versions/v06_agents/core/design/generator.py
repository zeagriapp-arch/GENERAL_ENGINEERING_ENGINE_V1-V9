"""
DesignGenerator (Phase 4): "No quiero que el LLM sea el diseñador
directamente." V1 ofrece dos estrategias intercambiables detrás de la
misma interfaz — ninguna es matemáticamente óptima (eso es Optimizer,
Phase 5); ambas solo exploran el Design Space respetando bounds.
"""
from __future__ import annotations

import itertools
import random
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from core.design.design_space import DesignSpace


class DesignGenerator(ABC):
    @abstractmethod
    def generate(self, design_space: DesignSpace, *, n: int, seed: Optional[int] = None) -> list[dict[str, float]]:
        """Devuelve hasta `n` puntos {nombre_variable: valor} dentro de los bounds del Design Space."""
        ...


class RandomSamplingGenerator(DesignGenerator):
    """Monte Carlo simple: uniforme dentro de cada bound, sin sesgo hacia ninguna región."""

    def generate(self, design_space: DesignSpace, *, n: int, seed: Optional[int] = None) -> list[dict[str, float]]:
        if not design_space.variables:
            return [{}]
        rng = random.Random(seed)
        return [
            {name: rng.uniform(v.lower_bound, v.upper_bound) for name, v in design_space.variables.items()}
            for _ in range(n)
        ]


class GridSweepGenerator(DesignGenerator):
    """Barrido determinista y reproducible — mismo seed/n siempre da el mismo grid."""

    def generate(self, design_space: DesignSpace, *, n: int, seed: Optional[int] = None) -> list[dict[str, float]]:
        var_names = list(design_space.variables)
        if not var_names:
            return [{}]

        if len(var_names) == 1:
            name = var_names[0]
            v = design_space.variables[name]
            return [{name: float(val)} for val in np.linspace(v.lower_bound, v.upper_bound, n)]

        per_axis = max(2, round(n ** (1.0 / len(var_names))))
        axes = [
            np.linspace(design_space.variables[name].lower_bound, design_space.variables[name].upper_bound, per_axis)
            for name in var_names
        ]
        points = [dict(zip(var_names, combo)) for combo in itertools.product(*axes)]
        return points[:n]
