"""
Requirements Engine (sección 9).

V1: expone la construcción programática y validación de `Requirements`.
La conversión NL -> Requirements vía LLM (Research/Design Agent) se
integra en Phase 6 — aquí se define el contrato que ese agente deberá
respetar: la salida SIEMPRE pasa por `RequirementsEngine.validate()`
antes de continuar el pipeline. Un LLM nunca produce un Requirements que
se use directamente sin pasar este gate.
"""
from __future__ import annotations

from core.requirements.schema import Requirements
from core.validation.dimensional_analysis import validate as validate_units


class RequirementsValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("Requirements inválidos: " + "; ".join(errors))


class RequirementsEngine:
    """Construye y valida Requirements estructurados."""

    def build(
        self,
        problem: str,
        domain: str,
        *,
        objectives: list | None = None,
        constraints: list | None = None,
        variables: dict | None = None,
        operating_conditions: dict | None = None,
        validation_requirements: list[str] | None = None,
    ) -> Requirements:
        req = Requirements(
            problem=problem,
            domain=domain,
            objectives=objectives or [],
            constraints=constraints or [],
            variables=variables or {},
            operating_conditions=operating_conditions or {},
            validation_requirements=validation_requirements or [],
        )
        self.validate(req)
        return req

    def validate(self, requirements: Requirements) -> None:
        """
        Gate dimensional obligatorio (sección 10). Lanza
        RequirementsValidationError si hay unidades inválidas en variables
        u operating_conditions. No permite que Requirements inconsistentes
        avancen al Knowledge/Design Engine.
        """
        errors: list[str] = []
        errors += [f"[variables] {e}" for e in validate_units(requirements.variables)]
        errors += [f"[operating_conditions] {e}" for e in validate_units(requirements.operating_conditions)]

        if not requirements.objectives:
            errors.append("Requirements sin al menos un Objective — no hay qué optimizar/evaluar.")

        if errors:
            raise RequirementsValidationError(errors)
