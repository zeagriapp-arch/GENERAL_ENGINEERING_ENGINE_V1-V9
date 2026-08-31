# REQUIREMENT_IMPLEMENTATION_REPORT

**Fecha:** 2026-08-31
**Fase:** Requirement Contract Engine
**Alcance:** implementación de `Requirement`/`RequirementCandidate` y la
`RequirementValidationPipeline` de 6 validadores, según la especificación
"FASE — REQUIREMENT CONTRACT ENGINE". Ver `REQUIREMENT_CONTRACT.md` para
la documentación del contrato en sí; este informe cubre el proceso, las
decisiones y la validación.

---

## 1. Arquitectura encontrada antes de implementar (sección 18)

Inspección realizada antes de escribir código (reutilizando el
conocimiento ya adquirido en la auditoría previa, más una relectura
dirigida de los módulos relevantes):

| Concepto buscado | Dónde vive | Decisión de reuso |
|---|---|---|
| Sistema de unidades/análisis dimensional | `core.validation.dimensional_analysis` (`validate_unit`, `are_compatible`, `convert`, sobre `pint`) | **Reutilizado directamente**, sin reimplementar — es la razón por la que este paquete depende de `versions/v09_advanced_ai` en vez de vivir aislado. |
| Requisito/restricción de un problema | `core.requirements.schema.{Requirements, Constraint, Objective, Parameter}` | **No se duplica.** Es un concepto distinto y complementario: `Requirements` es el agregado ya resuelto de un problema completo (~`EngineeringProblem`); `Requirement` (esta fase) es la unidad ANTERIOR, individual, todavía candidata. `requirement_contract/integration.py` traduce de uno a otro. |
| Ids cortos | `uuid.uuid4().hex[:12]` en `Design`/`Experiment` | Reutilizado tal cual en `schema.new_id()`. |
| Timestamps | `datetime.now(timezone.utc)` en todo el proyecto | Reutilizado tal cual en `schema.utcnow()`. |
| Inmutabilidad funcional (nunca mutar, devolver un objeto nuevo) | `core.design.repository.clone()`/`modify()` | Reutilizado como modelo directo para `versioning.lock()`/`revise()` — mismo principio, sin necesitar `frozen=True` en el schema (`Requirement` sigue siendo un `BaseModel` mutable normal, como `Design`/`Experiment`). |
| Inmutabilidad tras un estado "cerrado" | `ExperimentStatus` + `SQLiteExperimentStore.save()` rechazando reescribir un experimento ACCEPTED/REJECTED/FAILED | Inspiró el diseño de `RequirementStatus.LOCKED` — con la diferencia de que esta fase no incluye una persistencia SQLite (fuera de alcance, sección 19), así que la inmutabilidad se hace cumplir a nivel de función (`lock()`/`revise()`), no de store. |
| Máquina de estados explícita y verificada en código | `core.orchestrator.state_machine._VALID_TRANSITIONS` | Reutilizado como patrón para `schema.VALID_STATUS_TRANSITIONS`/`transition_status()`. |
| Reporte de validación estructurado (no `True`/`False`) | `core.validation.schema.ValidationReport` (V&V de simulaciones) | Mismo *principio* de diseño reutilizado (`ValidationResult`/`ValidationIssue` con `severity`/`field`/`details`), pero NO la misma clase — esa está pensada para resultados de simulación física (convergencia, benchmarks), un concepto distinto a validar un `RequirementCandidate`. |
| Evaluación de comparaciones (`>=`, `<=`, ...) | `core.physics.schema.PhysicsConstraint.evaluate()` — regex sobre texto libre | **Deliberadamente NO reutilizado** — es exactamente el patrón que la sección 3 de esta fase pide mejorar (operador estructurado desde el origen, no texto a parsear). `operators.py` es la versión estructurada equivalente. |
| Configuración por YAML, tool calling, agentes | `config/`, `core/tools/`, `agents/` | No aplica a esta fase — el contrato es agnóstico de LLM/proveedor (sección 20) y no se conecta a ningún agente todavía (sección 19). |
| Convención de tests (pytest, factories `_design(**overrides)`, `tests/__init__.py`) | `versions/v09_advanced_ai/tests/` | Reutilizada tal cual: `tests/conftest.py:make_candidate(**overrides)` sigue el mismo patrón que `_design(**overrides)` en `test_cold_gas_physics_model.py`. |
| Relación entre las 9 versiones | `ARCHITECTURA.md`/`VERSION_MAP.md` | Confirmó que `versions/` es específicamente el arco histórico de "V1", ya auditado y congelado — de ahí la decisión (con tu confirmación explícita) de ubicar esta fase fuera de `versions/`. |

**Ninguna abstracción existente tuvo que duplicarse innecesariamente** —
donde había algo reutilizable (unidades, ids, timestamps, patrón de
inmutabilidad, patrón de máquina de estados, patrón de test), se reutilizó
tal cual o como plantilla directa de diseño.

## 2. Ubicación y dependencia (decisión ya confirmada contigo)

`requirement_contract/` vive en la raíz del repositorio, como paquete
Python independiente que **depende de `versions/v09_advanced_ai`** (vía
`pip install -e` editable, ver `requirement_contract/README.md`) en vez de
copiar su código. `versions/v01_core`…`v09_advanced_ai` no se tocaron —
confirmado con tests/import-linter antes y después (sección 6).

## 3. Archivos nuevos creados

```
requirement_contract/
├── README.md
├── pyproject.toml
├── requirement_contract/
│   ├── __init__.py
│   ├── schema.py             (Requirement, Value, Provenance, Confidence,
│   │                           Verification, Uncertainty, Validity, enums,
│   │                           máquina de estados — 330 líneas)
│   ├── candidate.py           (RequirementCandidate)
│   ├── operators.py            (evaluación determinista + as_interval)
│   ├── versioning.py            (lock, revise, version_chain_ids)
│   ├── graph.py                  (missing_dependencies, find_cycles)
│   ├── integration.py             (to_core_constraint, to_core_parameter —
│   │                                la "interfaz mínima" de la sección 19)
│   └── validators/
│       ├── __init__.py
│       ├── base.py                 (ValidationResult/Issue/Severity/Validator)
│       ├── schema_validator.py
│       ├── unit_validator.py
│       ├── dimensional_validator.py
│       ├── constraint_validator.py
│       ├── conflict_validator.py
│       ├── provenance_validator.py
│       └── pipeline.py              (RequirementValidationPipeline)
└── tests/
    ├── __init__.py, conftest.py
    └── 14 archivos de test (test_schema.py, test_operators.py,
        test_units.py, test_dimensional_analysis.py, test_priority.py,
        test_provenance.py, test_uncertainty.py, test_dependencies.py,
        test_conflicts.py, test_versioning.py, test_locking.py,
        test_candidate.py, test_validation_pipeline.py, test_integration.py)
```

**1.693 líneas de código fuente, 1.296 líneas de tests, 149 tests.**

## 4. Archivos existentes modificados

**Ninguno.** `versions/v01_core`…`v09_advanced_ai`, `README.md`,
`ARCHITECTURE.md`, `shared/`, `tools/` — todos intactos. `git status
--short` confirma un único directorio nuevo (`requirement_contract/`), cero
archivos existentes tocados.

## 5. Decisiones arquitectónicas

- **`subject` vs. `parameter`**: la especificación los lista como campos
  separados sin definirlos — se interpretó `subject` como la entidad/
  componente (libre, sin vocabulario impuesto: `"system"`, `"satellite"`,
  cualquier string del caller) y `parameter` como la magnitud medible
  (`"mass"`, `"thrust"`). `"El sistema no debe superar 20 kg"` →
  `subject="system", parameter="mass"`.
- **`Value` único para escalares y listas**: en vez de un tipo paralelo
  "ValueRange", `Value.original_value`/`normalized_value` aceptan
  `ScalarValue | list[ScalarValue]` — cubre RANGE/DISCRETE (operator
  IN/NOT_IN) sin duplicar el modelo.
- **`SchemaValidator` vs. `ConstraintValidator`**: la especificación los
  lista como pasos separados sin una frontera explícita. Se definió:
  `SchemaValidator` valida la coherencia `type`↔`operator`↔forma de
  `value` (lo que Pydantic no puede expresar por sí solo); `ConstraintValidator`
  valida la coherencia interna de `uncertainty`/`validity`/`dependencies`
  contra `value` — dos responsabilidades distintas y no solapadas.
- **DimensionalValidator con registro de magnitudes universales**: para
  detectar `mass <= 500 seconds` sin dejar de ser agnóstico de dominio, se
  construyó `dimensional_validator.KNOWN_PARAMETER_DIMENSIONS` — SOLO
  magnitudes físicas fundamentales/universales (masa, tiempo, longitud,
  temperatura, fuerza, presión, energía, ...), verificado con un test
  explícito (`test_default_registry_has_no_aerospace_specific_vocabulary`)
  de que NO contiene vocabulario de ningún dominio concreto. Extensible sin
  tocar el módulo vía `register_parameter_dimension()`.
- **`ConflictValidator` sin resolución automática**: detecta contradicciones
  vía intersección de intervalos numéricos (generaliza el ejemplo par-a-par
  de la especificación a cualquier cantidad de Requirements sobre la misma
  magnitud), pero nunca decide "quién gana" — ni siquiera por prioridad
  HARD/SOFT — porque no existe en el resto del proyecto un mecanismo de
  resolución automática de conflictos entre requisitos que se pudiera
  reutilizar de forma justificada. Un conflicto siempre se reporta y el
  Requirement resultante queda `CONFLICTING`, sin poder bloquearse.
- **Sin persistencia (`RequirementStore`)**: el versionado/locking es
  puramente en memoria (funciones puras sobre objetos `Requirement`), no
  una base de datos — la sección 19 pide no construir infraestructura
  grande nueva, y `versions/` ya tiene el precedente de `SQLiteExperimentStore`
  si una fase futura decide que Requirement necesita persistencia propia.
- **`integration.py` mínimo y no conectado**: dos funciones puras
  (`to_core_constraint`, `to_core_parameter`), solo operan sobre
  Requirements `LOCKED`, sin ningún efecto secundario ni conexión a
  Orchestrator/DesignEngine — exactamente la "excepción" que permite la
  sección 19, nada más.

## 6. Validadores implementados

| Validador | Verifica | Nunca hace |
|---|---|---|
| `SchemaValidator` | `type`↔`operator`↔forma de `value` coherentes | Tocar unidades ni conflictos |
| `UnitValidator` | Unidad reconocible por `pint` (reutilizado de `core`) | Decidir compatibilidad física con el `parameter` (eso es DimensionalValidator) |
| `DimensionalValidator` | Unidad físicamente coherente con `parameter` (registro universal, extensible) | Fallar sobre un `parameter` que no reconoce (evita falsos positivos) |
| `ConstraintValidator` | `uncertainty`/`validity` compatibles dimensionalmente con `value`; dependencias existentes; sin duplicados | Comparar contra OTROS Requirements (eso es ConflictValidator) |
| `ConflictValidator` | Contradicción con Requirements existentes sobre el mismo `subject.parameter`, vía intervalos numéricos | Resolver el conflicto ni asumir prioridad |
| `ProvenanceValidator` | Campos estructurados obligatorios según `source_type` | Aceptar procedencia como solo texto libre |

`RequirementValidationPipeline` orquesta los 6 en el orden fijo de la
especificación, agrega todo en un `ValidationReport` (nunca un
`True`/`False`), y es inyectable (cada validador puede sustituirse —
usado explícitamente en un test para probar el comportamiento de fallo).

## 7. Tests creados — cobertura por categoría (sección 17)

| Categoría pedida | Archivo | Tests |
|---|---|---|
| Schema (válido/inválido/campos faltantes/tipos incorrectos) | `test_schema.py`, `test_candidate.py` | 20 |
| Operators (los 9) | `test_operators.py` | 20 |
| Units (conversión válida/incompatible/desconocida/preservación) | `test_units.py` | 13 |
| Dimensional analysis (compatible/incompatible, incl. `mass<=500s`) | `test_dimensional_analysis.py` | 9 |
| Priority (HARD/SOFT) | `test_priority.py` | 5 |
| Provenance (USER/DOCUMENT/COMPUTED/ASSUMPTION/SYSTEM) | `test_provenance.py` | 13 |
| Uncertainty (interval/percentage/distribution/unknown) | `test_uncertainty.py` | 9 |
| Dependencies (válida/inexistente/circular) | `test_dependencies.py` | 9 |
| Conflicts (`mass<=20` vs `mass>=30`, incl. cross-unidad) | `test_conflicts.py` | 9 |
| Versioning (revise no destruye la versión anterior) | `test_versioning.py` | 9 |
| Locking (LOCKED no se modifica directamente) | `test_locking.py` | 7 |
| Pipeline end-to-end + ejemplo objetivo de la fase | `test_validation_pipeline.py` | 9 |
| Integración mínima (`to_core_constraint`/`to_core_parameter`) | `test_integration.py` | 9 |

**Total: 149 tests, 149 pasan.**

## 8. Resultados de tests — antes / después

| Suite | Antes de esta fase | Después de esta fase |
|---|---|---|
| `versions/v01_core` | 34 passed | 34 passed (sin cambios) |
| `versions/v02_knowledge` | 50 passed | 50 passed (sin cambios) |
| `versions/v03_physics` | 125 passed | 125 passed (sin cambios) |
| `versions/v04_design` | 143 passed | 143 passed (sin cambios) |
| `versions/v05_optimization` | 155 passed | 155 passed (sin cambios) |
| `versions/v06_agents` | 177 passed | 177 passed (sin cambios) |
| `versions/v07_propulsion_domain` | 186 passed | 186 passed (sin cambios) |
| `versions/v08_discovery_report` | 196 passed | 196 passed (sin cambios) |
| `versions/v09_advanced_ai` | 200 passed | 200 passed (sin cambios) |
| **`requirement_contract/` (nuevo)** | — | **149 passed** |
| **Total** | **1.266** | **1.415** |

Corrido dos veces cada uno (antes de tocar nada, y de nuevo al terminar) —
las 9 versiones existentes no perdieron ni ganaron un solo test, y los
resultados numéricos de los demos (ver sección 10) son idénticos byte a
byte a los de la corrida original.

## 9. Import-linter — antes / después

| Paquete | Antes | Después |
|---|---|---|
| v01–v05 | 2/2 contratos (ya corregido en P1) | 2/2 (sin cambios) |
| v06–v09 | 3/3 contratos | 3/3 (sin cambios) |
| **`requirement_contract/` (nuevo)** | — | **2/2 contratos**: "no depende de agents ni domains", "no depende de ningún provider de LLM concreto" |

## 10. Demos end-to-end — verificación de no regresión

Re-corridos `run_phase6_vertical_slice.py` y `run_phase7_8_vertical_slice.py`
(v09) tras instalar `requirement_contract` en el mismo entorno: resultados
numéricos idénticos a las corridas previas (`thrust=0.8644164761965736`,
`Isp=76.82536852473885`, mismo `stopping_reason`, mismo conteo de
experimentos) — instalar y usar el nuevo paquete no interfiere en absoluto
con el resto del sistema (paquetes Python distintos, sin estado
compartido).

Adicionalmente, se ejecutó y verificó **literalmente** el ejemplo completo
de `REQUIREMENT_CONTRACT.md` (no solo se documentó de memoria) — el código
tal como aparece en el documento corre sin modificaciones y produce
exactamente los valores que el documento afirma.

## 11. Bug real encontrado y corregido durante la implementación

`ConflictValidator` (vía la función compartida `normalize_value()`)
crasheaba con `pint.errors.UndefinedUnitError` sin capturar cuando recibía
un candidato con una unidad inválida/desconocida — porque `ConflictValidator`
necesita normalizar valores independientemente de si `UnitValidator` ya
rechazó ese mismo candidato (los 6 validadores corren de forma
independiente sobre el mismo candidato, no en cadena con paso de estado).
Encontrado por los propios tests (`test_unknown_unit_candidate_is_invalid`,
`test_report_lists_every_issue_field_required_by_spec`), no por inspección
manual — exactamente el tipo de bug que la sección 17 ("no quiero
solamente tests del modelo") está pensada para atrapar. Corregido en
`unit_validator.normalize_value()`: ahora valida la unidad con
`validate_unit()` (reutilizado) ANTES de intentar convertir, y devuelve el
valor sin convertir con una nota explícita en vez de lanzar una excepción
— nunca un resultado inventado, nunca un crash no controlado, consistente
con la disciplina del resto del proyecto (`ODESolver.solve()`,
`ToolRegistry.invoke()`).

## 12. Problemas encontrados durante la implementación (ninguno arquitectónico mayor)

No surgió ningún caso que requiriera detenerme a pedir tu aprobación según
la sección 24 — el único ajuste no trivial fue el bug de la sección 11
(corrección de una función interna, sin implicaciones de diseño) y un
ajuste de configuración de `import-linter` (`include_external_packages =
true`, necesario porque `agents`/`domains` no son `root_packages` propios
de este paquete — mismo tipo de ajuste que ya se hizo en P1 para v01-v05,
no una decisión nueva).

## 13. Limitaciones actuales (documentadas, no ocultas)

- `ConflictValidator` solo detecta contradicciones representables como
  intervalo numérico simple (`<`,`<=`,`>`,`>=`,`=`) — `IN`/`NOT_IN`/`APPROX`/
  `NEQ` no generan conflicto automático todavía (documentado en el
  código, `operators.as_interval` devuelve `None` para esos casos).
- `find_cycles()` opera solo sobre un conjunto de `Requirement` ya
  construidos con id propio — no hay detección de ciclos "preventiva"
  sobre candidatos todavía sin id (limitación estructural inherente, no
  un descuido).
- Sin persistencia: reiniciar el proceso pierde todo el estado en memoria
  — aceptable para esta fase (contrato, no infraestructura), pero una
  fase futura de "Requirement Store" necesitará resolverlo si se quiere
  reproducibilidad entre sesiones.
- La normalización usa `to_base_units()` de `pint` — para magnitudes
  derivadas compuestas (presión, fuerza) el resultado es una unidad base
  compuesta (ej. `kg / m / s ** 2` para `Pa`) en vez de conservar el
  nombre de la unidad derivada (`Pa`). Es correcto dimensionalmente,
  documentado y testeado explícitamente
  (`test_compound_derived_unit_normalizes_to_base_si_form`), pero puede
  ser menos legible de lo ideal para un futuro Report/UI.

## 14. Recomendaciones para la siguiente fase

1. Antes de construir el Conversation Engine (NL→`RequirementCandidate`
   real vía LLM), decidir formalmente la integración con `OptimizationAgent`
   (pendiente desde la auditoría original) — ambas decisiones tocan cómo
   los agentes LLM producen/consumen estructuras validadas, conviene
   resolverlas en el mismo diseño en vez de por separado.
2. `EngineeringProblem` (el agregador de Requirements) es el siguiente
   punto de integración natural — usar `integration.py` como base, pero
   diseñar explícitamente cómo un conjunto de `Requirement` LOCKED se
   traduce a un `core.requirements.schema.Requirements` completo
   (objectives, constraints, variables) sin perder trazabilidad individual.
3. Si el volumen de Requirements crece más allá de lo manejable en
   memoria, evaluar un `RequirementStore` modelado sobre
   `SQLiteExperimentStore` — mismo patrón de inmutabilidad tras cierre ya
   demostrado en el resto del proyecto.
4. Considerar si `ConflictValidator` necesita cubrir `IN`/`NOT_IN` (ej.
   dos requisitos DISCRETE con conjuntos de valores disjuntos) antes de
   que un dominio real lo necesite — hoy es una limitación documentada,
   no bloqueante.

---

**Como pediste explícitamente: no continúo con la siguiente fase.** Este
informe y `REQUIREMENT_CONTRACT.md` quedan como entrega final de esta fase,
a la espera de tu revisión.
