"""
Generadores deterministas de referencia — generalizan
`core.design.generator.{GridSweepGenerator, RandomSamplingGenerator}`
(v09_advanced_ai, solo continuas) a los 5 tipos de `DesignDomain`
(sección 9): CONTINUOUS, INTEGER, DISCRETE, BOOLEAN, CATEGORICAL.
"""
from __future__ import annotations

import itertools
import random
from typing import Optional

import numpy as np

from design_contract.candidate import CandidateDesign
from design_contract.design_space import DesignSpace
from design_contract.generators.base import DesignGenerator, GeneratorKind
from design_contract.schema import DesignProvenance, DesignProvenanceSource
from design_contract.variables import DesignDomainType, DesignVariable, VariableRole


def _candidate_from_values(design_space: DesignSpace, values: dict, generator_id: str) -> CandidateDesign:
    return CandidateDesign(
        design_space_id=design_space.id,
        variable_values=values,
        provenance=DesignProvenance(source_type=DesignProvenanceSource.GENERATED, generator_id=generator_id),
    )


def _axis_values(var: DesignVariable, *, per_axis: int, rng: Optional[random.Random] = None) -> list:
    """Puntos representativos de un dominio para un barrido tipo grid — o un único valor aleatorio si `rng` se provee."""
    domain = var.domain
    if domain.kind == DesignDomainType.CONTINUOUS:
        if rng is not None:
            return [rng.uniform(domain.lower_bound, domain.upper_bound)]
        # float(v) explícito — mismo patrón que core.design.generator.GridSweepGenerator
        # (v09_advanced_ai): np.linspace produce numpy.float64, que de dejarse sin
        # convertir propaga numpy.bool_ en comparaciones posteriores (DesignConstraint.evaluate()
        # exige un bool nativo). Bug real encontrado por el test de integración completo — ver
        # DESIGN_DESIGNSPACE_IMPLEMENTATION_REPORT.md.
        return [float(v) for v in np.linspace(domain.lower_bound, domain.upper_bound, per_axis)]
    if domain.kind == DesignDomainType.INTEGER:
        lo, hi = int(domain.lower_bound), int(domain.upper_bound)
        if rng is not None:
            return [rng.randint(lo, hi)]
        span = hi - lo + 1
        count = min(per_axis, span)
        return sorted(set(int(v) for v in np.linspace(lo, hi, count)))
    # DISCRETE / CATEGORICAL / BOOLEAN
    values = list(domain.allowed_values or [])
    if rng is not None:
        return [rng.choice(values)] if values else []
    return values


class RandomSamplingDesignGenerator(DesignGenerator):
    """Muestreo uniforme/aleatorio dentro de cada dominio — sin sesgo hacia ninguna región."""

    id = "random_sampling"
    kind = GeneratorKind.PARAMETER

    def generate(self, design_space: DesignSpace, *, n: int, seed: Optional[int] = None) -> list[CandidateDesign]:
        free_vars = {
            name: var for name, var in design_space.variables.items() if var.role in (VariableRole.DESIGN, VariableRole.CONTROL)
        }
        if not free_vars:
            return [_candidate_from_values(design_space, {}, self.id)]

        rng = random.Random(seed)
        candidates = []
        for _ in range(n):
            values = {name: _axis_values(var, per_axis=1, rng=rng)[0] for name, var in free_vars.items()}
            candidates.append(_candidate_from_values(design_space, values, self.id))
        return candidates


class GridSweepDesignGenerator(DesignGenerator):
    """Barrido determinista y reproducible sobre el producto cartesiano de ejes representativos."""

    id = "grid_sweep"
    kind = GeneratorKind.PARAMETER

    def generate(self, design_space: DesignSpace, *, n: int, seed: Optional[int] = None) -> list[CandidateDesign]:
        free_vars = {
            name: var for name, var in design_space.variables.items() if var.role in (VariableRole.DESIGN, VariableRole.CONTROL)
        }
        if not free_vars:
            return [_candidate_from_values(design_space, {}, self.id)]

        names = list(free_vars)
        per_axis = max(2, round(n ** (1.0 / len(names)))) if len(names) > 1 else n
        axes = [_axis_values(free_vars[name], per_axis=per_axis) for name in names]
        combos = itertools.product(*axes)
        candidates = [_candidate_from_values(design_space, dict(zip(names, combo)), self.id) for combo in combos]
        return candidates[:n]
