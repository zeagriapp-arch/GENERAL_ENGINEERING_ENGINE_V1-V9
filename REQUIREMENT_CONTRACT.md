# REQUIREMENT_CONTRACT.md

Documentación del contrato central implementado en `requirement_contract/`
(raíz del repositorio, fuera de `versions/` — depende de
`versions/v09_advanced_ai` como paquete, no como copia; ver
`requirement_contract/README.md`).

---

## 1. Qué es `Requirement`

`Requirement` es la unidad fundamental de una condición de ingeniería,
independiente de dominio: no sabe nada de satélites, propulsión, CFD, FEA
ni ningún otro dominio concreto. Representa una única afirmación
verificable como "el sistema no debe superar 20 kg", estructurada en
campos deterministas (sujeto, parámetro, operador, valor, unidad) en vez
de texto libre.

Principio fundamental: **el LLM nunca tiene autoridad para crear un
`Requirement` directamente**. Solo puede proponer un `RequirementCandidate`
(sección 2), que la `RequirementValidationPipeline` (sección 13) valida
determinísticamente antes de que exista un `Requirement`.

```
USER -> LLM -> RequirementCandidate -> Schema Validation -> Unit/Dimensional
Validation -> Constraint Validation -> Conflict Detection -> Provenance
Validation -> Requirement -> (EngineeringProblem, fase futura)
```

## 2. `RequirementCandidate` vs. `Requirement`

| | `RequirementCandidate` | `Requirement` |
|---|---|---|
| Quién lo produce | Cualquier fuente no confiable (típicamente un LLM) | Solo la validation pipeline |
| Tiene `id`/`version`/`status` | No | Sí |
| Tiene `verification` | No (el proponente no puede auto-verificarse) | Sí — asignado por la pipeline |
| Valor | Solo `value_original`/`value_unit`, sin normalizar | `value.normalized_*` ya calculado |
| Autoridad | Ninguna — no se persiste, no se referencia como dependencia de nadie | Es la representación oficial, versionada, trazable |

`RequirementCandidate` es un `pydantic.BaseModel` normal — el mismo tipo de
objeto que ya se usa como `response_schema=` en
`core.models.interfaces.ModelProvider.complete()` en el resto del proyecto
(ver `agents/base.py:Agent.ask()`). No está acoplado a Ollama, OpenAI,
Claude ni ningún proveedor — cualquier `ModelProvider` que produzca JSON
válido contra este schema sirve.

## 3. Estados (`RequirementStatus`)

```
DRAFT -> PARSED -> NORMALIZED -> VALIDATED -> LOCKED
                        |            |
                        v            v
                    INVALID    CONFLICTING / BLOCKED
```

Transiciones controladas explícitamente en código
(`schema.VALID_STATUS_TRANSITIONS` + `transition_status()`), igual en
espíritu a `core.orchestrator.state_machine` del resto del proyecto.
`LOCKED` es terminal: no tiene transiciones salientes. La única forma de
"cambiar" un Requirement `LOCKED` es `versioning.revise()`, que produce una
versión **nueva** en `DRAFT`, nunca muta la existente.

## 4. Tipos (`RequirementType`)

`LIMIT`, `TARGET`, `RANGE`, `EQUALITY`, `INEQUALITY`, `BOOLEAN`,
`DISCRETE`, `QUALITATIVE`. Cada uno restringe qué operadores son válidos
(`SchemaValidator`) — ej. `RANGE` solo admite `IN` con una lista de 2
valores ascendentes; `BOOLEAN` solo admite `EQ`/`NEQ` sobre un valor
booleano.

## 5. Operadores (`Operator`)

`=`, `!=`, `<`, `<=`, `>`, `>=`, `IN`, `NOT_IN`, `APPROX` — un enum
estructurado, nunca texto natural. Evaluados determinísticamente en
`operators.evaluate()`. Contraste deliberado con
`core.physics.schema.PhysicsConstraint.evaluate()` (resto del proyecto),
que parsea una expresión de texto con regex: aquí no hay texto que
parsear, el operador ya es estructurado desde que el LLM lo propone.

## 6. Unidades (`Value`)

```python
class Value:
    original_value   # tal como lo propuso la fuente — NUNCA se descarta
    original_unit
    normalized_value  # calculado por UnitValidator, unidad base SI
    normalized_unit
    conversion_notes   # registro explícito de la conversión — nunca silenciosa
```

La conversión reutiliza `core.validation.dimensional_analysis` de
`versions/v09_advanced_ai` (`validate_unit`, `convert`) — no se
reimplementa un segundo sistema de unidades. Ejemplo: `20 lb` normaliza a
`9.0718474 kg`, con una nota explícita de la conversión aplicada.

Dos validadores distintos cubren "unidad" y "dimensión" por separado:

- **`UnitValidator`**: ¿la unidad en sí es reconocible por `pint`? (`'seconds'`
  es válida como unidad).
- **`DimensionalValidator`**: ¿la unidad es *físicamente coherente* con el
  `parameter`? Detecta `mass <= 500 seconds` (unidad válida, dimensión
  incorrecta) contra un registro de magnitudes físicas universales
  (`dimensional_validator.KNOWN_PARAMETER_DIMENSIONS` — solo SI base +
  derivadas comunes: masa, longitud, tiempo, temperatura, fuerza, presión,
  energía, potencia, velocidad, densidad, etc. — deliberadamente sin
  vocabulario de ningún dominio concreto). Extensible sin tocar el módulo
  vía `register_parameter_dimension(nombre, unidad_referencia)`.

## 7. Provenance

```python
class Provenance:
    source_type: USER | DOCUMENT | COMPUTED | ASSUMPTION | SYSTEM
    actor           # quién/qué lo originó
    document_id      # obligatorio si DOCUMENT
    derivation_id     # obligatorio si COMPUTED
    derived_from       # ids de origen, obligatorio si COMPUTED
    assumption_text    # obligatorio si ASSUMPTION
```

`ProvenanceValidator` exige los campos estructurados obligatorios según
`source_type` — nunca acepta procedencia como solo texto libre.

## 8. Confidence vs. Verification

Deliberadamente separados:

```python
class Confidence:      # opinión del proponente — nunca decide nada
    level: LOW | MEDIUM | HIGH | UNKNOWN
    score: float | None   # 0-1, informativo

class Verification:    # hecho objetivo — lo asigna la pipeline, nunca el LLM
    status: UNVERIFIED | VERIFIED | REJECTED | NEEDS_REVIEW
    verified_by: str | None
```

Un LLM puede reportar `confidence.level = HIGH` y estar equivocado —
`verification.status` solo pasa a `VERIFIED` cuando la
`RequirementValidationPipeline` completa sin errores, nunca por la sola
afirmación del proponente.

## 9. Uncertainty

```python
class Uncertainty:
    type: NONE | UNKNOWN | INTERVAL | PERCENTAGE | DISTRIBUTION
    lower, upper          # si INTERVAL
    percentage             # si PERCENTAGE
    distribution_name, distribution_params  # si DISTRIBUTION
```

Contrato suficiente para uso futuro (Monte Carlo, propagación de
incertidumbre) — sin implementar ese motor en esta fase. Validado
estructuralmente (`Uncertainty` exige los campos correctos según `type`
vía `model_validator`).

## 10. Validity

```python
class Validity:
    conditions: dict[str, ValidityRange]  # ej. {"temperature": ValidityRange(min=250, max=400, unit="K")}
```

Extensible y agnóstico de dominio: un dict abierto, no una lista fija de
campos aeroespaciales.

## 11. Dependencies

`Requirement.dependencies: list[str]` — ids de otros Requirements de los
que este depende (ej. `R002.dependencies = ["R001"]` si
`propellant_mass <= mass`). `ConstraintValidator` verifica que las
dependencias existan entre los Requirements conocidos; `graph.find_cycles()`
detecta referencias circulares sobre un conjunto de Requirements ya
construidos (los candidatos no tienen id propio todavía, así que un ciclo
solo puede detectarse una vez que existen ≥2 Requirements).

## 12. Conflicts

`ConflictValidator` traduce cada comparación numérica
(`<`,`<=`,`>`,`>=`,`=`) a un intervalo en la recta real
(`operators.as_interval`) en unidades normalizadas, y verifica que la
intersección con todos los Requirements existentes sobre el mismo
`subject.parameter` sea no vacía. `mass <= 20 kg` (existente) vs.
`mass >= 30 kg` (candidato) → intervalos `(-inf, 20]` y `[30, inf)` →
intersección vacía → `CONFLICTING`. Nunca decide automáticamente cuál
"gana" por prioridad — se informa el conflicto y el Requirement resultante
queda marcado `CONFLICTING`, sin poder bloquearse (`lock()` lo rechaza)
hasta que se resuelva.

## 13. Validation Pipeline

```
RequirementCandidate
   -> SchemaValidator        (type/operator/value coherentes entre sí)
   -> UnitValidator            (unidad reconocible, normalización)
   -> DimensionalValidator      (unidad físicamente coherente con parameter)
   -> ConstraintValidator        (uncertainty/validity/dependencies coherentes)
   -> ConflictValidator            (contradice algún Requirement existente?)
   -> ProvenanceValidator            (procedencia estructuralmente completa)
   -> Requirement (VALIDATED | CONFLICTING) | None (INVALID)
```

Cada validador devuelve un `ValidationResult` estructurado (nunca
`True`/`False`): `validator`, `severity` (`INFO`/`WARNING`/`ERROR`),
`message`, `field`, `details`. `ValidationReport` agrega los resultados de
los 6 validadores y expone `overall_status`, `all_issues`, `is_valid`.

`RequirementValidationPipeline` es inyectable (cada validador puede
sustituirse, útil para tests) y expone `validate_candidate()` como atajo
de conveniencia sobre una instancia por defecto.

## 14. Versioning y Locking

- `versioning.lock(requirement)`: solo desde `VALIDATED` → `LOCKED`.
  Nunca muta — devuelve una copia.
- `versioning.revise(requirement, changes)`: produce un Requirement
  **nuevo** (`id` nuevo, `version = version + 1`,
  `previous_version_id = requirement.id`, `status` reiniciado a `DRAFT` —
  toda revisión debe volver a pasar por la pipeline completa). El
  Requirement original nunca se modifica ni se elimina.
- Modelado directamente sobre `core.design.repository.clone()`/`modify()`
  del resto del proyecto — mismo principio de inmutabilidad funcional, sin
  necesitar `frozen=True` en el schema.

---

## Ejemplo completo

**Entrada:** "El sistema no debe superar 20 kg"

```python
from requirement_contract.candidate import RequirementCandidate
from requirement_contract.schema import Operator, Priority, Provenance, ProvenanceSource, RequirementType
from requirement_contract.validators.pipeline import validate_candidate
from requirement_contract.versioning import lock

candidate = RequirementCandidate(
    subject="system",
    parameter="mass",
    type=RequirementType.LIMIT,
    operator=Operator.LTE,
    value_original=20.0,
    value_unit="kg",
    priority=Priority.HARD,
    provenance=Provenance(source_type=ProvenanceSource.USER, actor="ingeniero-sistemas"),
    source_text="El sistema no debe superar 20 kg",
)

requirement, report = validate_candidate(candidate)
assert report.is_valid                                  # True
assert requirement.value.normalized_value == 20.0        # normalizado (ya en kg)
assert requirement.verification.status.value == "VERIFIED"

locked = lock(requirement)                                 # Locked Requirement
print(locked)
# system.mass <= 20.0 kg [HARD]
```

`requirement` resultante (resumen de todos los campos del contrato):

| Campo | Valor |
|---|---|
| `subject` / `parameter` | `system` / `mass` |
| `type` / `operator` | `LIMIT` / `<=` |
| `value.original` | `20.0 kg` |
| `value.normalized` | `20.0 kg` |
| `priority` | `HARD` |
| `provenance` | `USER`, actor=`ingeniero-sistemas` |
| `confidence` | `UNKNOWN` (no reportada por el proponente) |
| `verification` | `VERIFIED`, por `RequirementValidationPipeline` |
| `uncertainty` | `NONE` |
| `validity` | `{}` (sin restricciones adicionales) |
| `dependencies` | `[]` |
| `version` / `status` | `1` / `LOCKED` (tras `lock()`) |

Integración mínima (sección 19 de la especificación, sin conectar a ningún
pipeline vivo — ver `requirement_contract/integration.py`):

```python
from requirement_contract.integration import to_core_constraint

constraint = to_core_constraint(locked)
# core.requirements.schema.Constraint(name="system.mass:...", expression="mass <= 20.0", unit="kg", hard=True)
```

---

## Qué NO cubre esta fase

- Conversion Engine / extracción NL→`RequirementCandidate` real vía LLM.
- `EngineeringProblem` (agregador de muchos Requirements en un problema
  completo) — solo existen `to_core_constraint`/`to_core_parameter` como
  puente mínimo hacia `core.requirements.schema`.
- Persistencia (`RequirementStore`) — versionado/locking es en memoria.
- Resolución automática de conflictos, motor de grafos avanzado, Monte
  Carlo/propagación de incertidumbre real, Design Engine.

Ver `REQUIREMENT_IMPLEMENTATION_REPORT.md` para el detalle de qué se
reutilizó, qué se creó, y los resultados de validación.
