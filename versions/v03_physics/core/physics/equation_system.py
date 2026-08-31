"""
EquationSystem (sección 6): representación estructurada de ecuaciones
con verificación automática ANTES de que lleguen al solver (sección 7 —
"una inconsistencia dimensional debe detener la simulación").

Distinto de `core.knowledge.schema.Equation` (esa es la versión
consultable/citable del Knowledge Engine, para RAG y provenance). Esta
es la versión que el motor usa para VALIDAR antes de ejecutar.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from core.validation.dimensional_analysis import validate_unit


class EquationSpec(BaseModel):
    equation_id: str
    expression: str
    variables: dict[str, str] = Field(description="símbolo -> descripción")
    parameters: list[str] = Field(default_factory=list, description="nombres de parámetros requeridos")
    units: dict[str, str] = Field(default_factory=dict, description="símbolo -> unidad")
    assumptions: list[str] = Field(default_factory=list)
    validity_range: dict[str, tuple[float, float]] = Field(default_factory=dict)
    source: Optional[str] = None
    version: str = "1.0"


class EquationValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("EquationSystem inválido: " + "; ".join(errors))


class EquationSystem:
    """Sección 6/7: 'NO permitir ecuaciones incompletas sin generar un error explícito'."""

    def __init__(self, equations: list[EquationSpec]):
        self.equations: dict[str, EquationSpec] = {eq.equation_id: eq for eq in equations}

    def validate(
        self, available_variables: set[str], available_parameters: set[str]
    ) -> list[str]:
        """
        Verifica, para cada ecuación: variables existentes, parámetros
        requeridos disponibles, y unidades declaradas válidas. Devuelve
        la lista de errores (vacía == válido) — no lanza excepción por
        sí sola para que el caller decida (ver `validate_or_raise`).
        """
        errors: list[str] = []
        known = available_variables | available_parameters
        for eq in self.equations.values():
            missing_vars = set(eq.variables) - known
            if missing_vars:
                errors.append(f"[{eq.equation_id}] variables no disponibles: {sorted(missing_vars)}")

            missing_params = set(eq.parameters) - available_parameters
            if missing_params:
                errors.append(f"[{eq.equation_id}] parámetros requeridos faltantes: {sorted(missing_params)}")

            for symbol, unit in eq.units.items():
                result = validate_unit(unit if unit else None)
                if not result.valid:
                    errors.append(f"[{eq.equation_id}] unidad inválida para '{symbol}': '{unit}' ({result.reason})")
        return errors

    def validate_or_raise(self, available_variables: set[str], available_parameters: set[str]) -> None:
        errors = self.validate(available_variables, available_parameters)
        if errors:
            raise EquationValidationError(errors)

    def get(self, equation_id: str) -> EquationSpec:
        return self.equations[equation_id]
