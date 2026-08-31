"""
DimensionalValidator (sección 14, paso 2 / sección 6).

Distinto de `UnitValidator`: ese valida que la unidad *en sí* sea
reconocible ('seconds' es una unidad perfectamente válida). Este valida
que la unidad sea *físicamente coherente con el `parameter`* — para
detectar el caso explícito de la especificación: `mass <= 500 seconds`
(unidad válida, pero incompatible con lo que 'mass' debería medir).

Para seguir siendo independiente de dominio (sección 1 de esta fase:
"NO debe contener lógica específica de satélites/cohetes/..."), el
registro de abajo cubre EXCLUSIVAMENTE las magnitudes físicas
fundamentales/universales (las 7 magnitudes base del SI + las derivadas
coherentes más comunes de cualquier curso introductorio de física/
mecánica) — nunca vocabulario específico de un dominio ("thrust",
"specific_impulse", "chamber_pressure", etc. NO están aquí a propósito).
Un futuro Domain Pack puede extender el registro vía
`register_parameter_dimension()` sin tocar este módulo.

Si `parameter` no está en el registro, el validador no puede afirmar nada
y no reporta error — evita falsos positivos sobre nombres de parámetro que
no reconoce, en vez de asumir que todo lo desconocido está mal.
"""
from __future__ import annotations

from core.validation.dimensional_analysis import are_compatible

from requirement_contract.candidate import RequirementCandidate
from requirement_contract.validators.base import Severity, ValidationContext, ValidationResult, Validator

# nombre de parámetro (minúsculas) -> unidad de referencia de su dimensión esperada.
# Solo magnitudes físicas universales — ver docstring del módulo.
KNOWN_PARAMETER_DIMENSIONS: dict[str, str] = {
    "mass": "kg",
    "time": "s",
    "duration": "s",
    "length": "m",
    "distance": "m",
    "height": "m",
    "width": "m",
    "depth": "m",
    "radius": "m",
    "diameter": "m",
    "area": "m^2",
    "volume": "m^3",
    "temperature": "K",
    "pressure": "Pa",
    "force": "N",
    "energy": "J",
    "power": "W",
    "velocity": "m/s",
    "speed": "m/s",
    "acceleration": "m/s^2",
    "density": "kg/m^3",
    "frequency": "Hz",
    "voltage": "V",
    "current": "A",
    "resistance": "ohm",
    "charge": "C",
    "angle": "rad",
    "torque": "N*m",
}


def register_parameter_dimension(parameter_name: str, reference_unit: str) -> None:
    """
    Punto de extensión explícito para futuros Domain Packs (sección 6:
    "el diseño debe permitir añadir dominios sin tocar el núcleo"). No se
    usa en esta fase por ningún dominio concreto.
    """
    KNOWN_PARAMETER_DIMENSIONS[parameter_name.strip().lower()] = reference_unit


class DimensionalValidator(Validator):
    name = "dimensional_validator"

    def validate(self, candidate: RequirementCandidate, *, context: ValidationContext) -> ValidationResult:
        issues = []

        expected_unit = KNOWN_PARAMETER_DIMENSIONS.get(candidate.parameter.strip().lower())
        if expected_unit is not None and candidate.value_unit is not None:
            if not are_compatible(candidate.value_unit, expected_unit):
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="value_unit",
                        message=(
                            f"Incompatibilidad dimensional: parameter='{candidate.parameter}' se espera en "
                            f"unidades de '{expected_unit}', pero se declaró '{candidate.value_unit}'."
                        ),
                        expected_dimension_reference=expected_unit,
                    )
                )

        # Misma verificación para uncertainty, si trae unidad propia distinta a value_unit.
        if expected_unit is not None and candidate.uncertainty.unit is not None:
            if not are_compatible(candidate.uncertainty.unit, expected_unit):
                issues.append(
                    self._issue(
                        severity=Severity.ERROR,
                        field="uncertainty.unit",
                        message=(
                            f"Incompatibilidad dimensional en uncertainty: parameter='{candidate.parameter}' "
                            f"espera '{expected_unit}', uncertainty declara '{candidate.uncertainty.unit}'."
                        ),
                    )
                )

        passed = not any(i.severity == Severity.ERROR for i in issues)
        return self._result(passed=passed, issues=issues)
