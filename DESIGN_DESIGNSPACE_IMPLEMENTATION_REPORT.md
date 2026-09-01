# DESIGN_DESIGNSPACE_IMPLEMENTATION_REPORT

**Fecha:** 2026-09-01
**Fase:** Design & DesignSpace Engine
**Alcance:** `Design`, `DesignSpace`, `DesignVariable`/`DesignDomain`,
`DesignRelation`/`CandidateRelation` (DSL seguro), `DesignConstraint`,
`DesignObjective`/`ObjectiveVector`, `CandidateDesign`, `DesignGenerator`,
`FeasibilityChecker`, `DesignLineage`, `SearchSpace`, `Novelty`,
`ExperimentBudget`. Ver `DESIGN_DESIGNSPACE_CONTRACT.md` para el contrato
en sí; este informe cubre el proceso, las decisiones y la validación.

---

## 1. Arquitectura encontrada antes de implementar (sección 34)

| Concepto buscado | Dónde vive | Decisión |
|---|---|---|
| `Design`/`Component`/`MaterialRef`/`ComponentInterface` | `core.design.schema` (v09_advanced_ai) | **No duplicado, superado deliberadamente.** Esa clase es la representación ya cableada a `DesignEngine`/`OptunaOptimizer`, probada con física real (155+ tests) — pero solo tiene variables continuas, `geometry` como `dict` sin tipar, `provenance` como `list[str]`, sin roles ni lineage de hijos. `design_contract.Design` es la capa de AUTORÍA/DESCUBRIMIENTO, un nivel antes en el pipeline — mismo patrón que `Requirement` (fase anterior) frente a `core.requirements.schema.Requirements`. |
| `DesignSpace`/`DesignVariable` (solo bounds continuos) | `core.design.design_space` | Generalizado a 5 tipos de dominio (`DesignDomain`), no reescrito — la clase original sigue intacta y en uso. |
| `DesignGenerator` (grid/random, solo continuo) | `core.design.generator` | Generalizado en `design_contract.generators.deterministic` a los 5 tipos de dominio — mismo patrón (`GridSweepGenerator`/`RandomSamplingGenerator`), extendido, no reemplazado. |
| Sistema de unidades | `core.validation.dimensional_analysis` | Reutilizado indirectamente vía `requirement_contract.validators.unit_validator.normalize_value` (que ya lo reutiliza) — no se reimplementa un tercer sistema de unidades. |
| `Value`/`Provenance`/`Uncertainty`/`Priority` | `requirement_contract.schema` | **Reutilizados directamente** para: valores con unidad (`Value`, en `Material.properties`, `Design.parameters`), incertidumbre de propiedades de material (`Uncertainty`), HARD/SOFT (`Priority`, en `DesignConstraint` — sección 13 lo pide explícitamente), y provenance epistémica de `DesignVariable` (por qué reutilizar y por qué NO reutilizar para `Design`/`CandidateDesign` en sí, ver sección 5 de este informe). |
| Resultado de validación estructurado (`ValidationResult`/`Severity`/`Issue`) | `requirement_contract.validators.base` | **Reutilizado directamente**, sin redefinir — es infraestructura genérica, no específica de Requirements. Solo se define un `DesignValidationContext` propio (nombre de campo distinto, `known_designs` en vez de `known_requirements`). |
| Patrón de inmutabilidad funcional (`clone`/`modify`, nunca mutar) | `core.design.repository` | Modelo directo para `design_contract.versioning.lock()`/`revise()` — mismo principio, aplicado a `Design` en vez de a `Design` de v09 (evita confusión: son namespaces distintos, `design_contract.Design` vs. `core.design.schema.Design`). |
| Inmutabilidad tras estado cerrado | `ExperimentStatus` + `SQLiteExperimentStore` | Inspiró `DesignStatus.LOCKED` — sin persistencia SQLite en esta fase (fuera de alcance, sección 35), la inmutabilidad se hace cumplir a nivel de función, igual que en la fase de Requirement. |
| Optimizer/Budget existentes | `core.orchestrator.budget.Budget`, `core.optimization.*` | `Budget` **no se reutiliza tal cual** para `ExperimentBudget` — campos genuinamente distintos (`max_candidates`/`max_cost` no existen en `Budget`; `max_llm_calls`/`max_research_calls` no aplican a exploración de DesignSpace). Documentado explícitamente en `budget.py` por qué no es un simple renombrado. |
| `Objective`/`Constraint` (dentro de `Requirements`) | `core.requirements.schema` | No duplicado en el sentido de "mismo dato, dos representaciones" — `DesignObjective`/`DesignConstraint` viven en `DesignSpace` (nivel de autoría), `Objective`/`Constraint` viven en `Requirements` (nivel de ejecución) — mismo split ya establecido entre `Requirement` y `core.requirements.schema.Requirements`. |
| Convención de tests | `versions/v09_advanced_ai/tests/`, `requirement_contract/tests/` | Reutilizada tal cual: factories `make_variable(**overrides)`/`cylinder_design_space(**overrides)` en `conftest.py`, mismo estilo de clases `TestXxx` con un método por caso. |

**Ninguna abstracción existente se duplicó sin justificación** — donde
algo ya resolvía el problema (unidades, ids, timestamps, patrón de
inmutabilidad, resultado de validación estructurado), se reutilizó
directamente; donde el contrato pedido era genuinamente más rico que lo
existente (variables con rol y 5 tipos de dominio, geometría/materiales
extensibles, lineage de generación, CandidateDesign con autoridad menor),
se construyó nuevo, documentando explícitamente por qué no bastaba
extender la clase existente in situ.

## 2. Ubicación y dependencias

`design_contract/` vive en la raíz del repositorio, como paquete Python
independiente — mismo patrón exacto que `requirement_contract/` (fase
anterior, ya aprobado). Depende de `versions/v09_advanced_ai` (`core.design.schema`,
`core.requirements.schema`, indirectamente `core.validation.dimensional_analysis`)
y de `requirement_contract` (`Value`, `Provenance`, `Priority`,
`Uncertainty`, infraestructura de validación) vía `pip install -e`
editable — ninguno de los dos se copia ni se modifica.

**Ningún archivo existente se modificó.** `versions/v01_core`…`v09_advanced_ai`
y `requirement_contract/` quedaron completamente intactos — confirmado
con tests/import-linter antes y después (sección 8).

## 3. Archivos nuevos creados

```
design_contract/
├── README.md, pyproject.toml
├── design_contract/
│   ├── __init__.py
│   ├── schema.py              (Design, Component, Architecture, Geometry,
│   │                            Material, DesignProvenance, DesignStatus — 260 líneas)
│   ├── variables.py            (DesignDomain, DesignVariable, VariableRole)
│   ├── relations.py             (DSL seguro — AST whitelist, DesignRelation,
│   │                              CandidateRelation — 260 líneas, el módulo
│   │                              más crítico de seguridad de esta fase)
│   ├── constraints.py            (DesignConstraint)
│   ├── objectives.py              (DesignObjective, ObjectiveVector, dominancia Pareto)
│   ├── design_space.py             (DesignSpace, estimate_size, validate_internal_consistency)
│   ├── search_space.py              (SearchSpace, SearchStrategyKind)
│   ├── candidate.py                  (CandidateDesign)
│   ├── lineage.py                     (DesignLineage, generación/transformación)
│   ├── feasibility.py                  (FeasibilityChecker, StructuralFeasibilityChecker)
│   ├── novelty.py                       (NoveltyScorer, ParameterDistanceNoveltyScorer)
│   ├── budget.py                         (ExperimentBudget)
│   ├── integration.py                     (to_core_design — interfaz mínima, sin conectar)
│   ├── generators/
│   │   ├── base.py                          (DesignGenerator, GeneratorKind)
│   │   └── deterministic.py                  (GridSweepDesignGenerator, RandomSamplingDesignGenerator)
│   └── validators/
│       ├── base.py                            (reexporta requirement_contract + DesignValidationContext)
│       ├── schema_validator.py, structural_validator.py, unit_validator.py, constraint_validator.py
│       └── pipeline.py                         (DesignValidationPipeline)
└── tests/
    ├── conftest.py
    └── 18 archivos de test
```

**2.046 líneas de código fuente, 1.507 líneas de tests, 183 tests.**

## 4. Archivos existentes modificados

**Ninguno.**

## 5. Decisiones arquitectónicas

- **`subject`/`type` de la spec, resueltos como propiedades derivadas, no campos guardados**: `DesignVariable.type` es una `@property` que devuelve `domain.kind` — evita que dos campos (`type` guardado + `domain.kind`) puedan desincronizarse. Mismo principio aplicado a `Requirement` en la fase anterior.
- **`DesignDomain` sin `unit` propio**: `DesignVariable.unit` es la única fuente de verdad — un dominio no lleva su propia unidad para no tener dos lugares que puedan quedar inconsistentes.
- **Dos vocabularios de provenance, deliberadamente distintos**: `DesignProvenanceSource` (USER/GENERATED/IMPORTED/DERIVED/OPTIMIZED/LLM_PROPOSED/SYSTEM, procedimental — cómo se produjo un Design) vs. `requirement_contract.schema.ProvenanceSource` (USER/DOCUMENT/COMPUTED/ASSUMPTION/SYSTEM, epistémico — de dónde salió una afirmación). Se reutiliza el SEGUNDO para `DesignVariable.provenance` (una variable y sus bounds son epistémicamente más parecidos a un Requirement) pero NO para `Design`/`CandidateDesign` (donde GENERATED/OPTIMIZED/LLM_PROPOSED no tienen equivalente epistémico razonable). Verificado con un test explícito de que ambos vocabularios son conjuntos distintos.
- **DSL seguro de expresiones, denegación por defecto**: en vez de una lista negra de construcciones prohibidas (que siempre puede quedar incompleta), `_SafeEvaluator`/`_StructureChecker` exigen un `visit_*` explícito por tipo de nodo AST — cualquier cosa sin uno se rechaza automáticamente. Se registran funciones seguras explícitamente (`register_relation_function`), nunca se ejecuta texto propuesto por un LLM como código.
- **"Constraint validation" + "Feasibility" colapsan en un solo validador** (`ConstraintValidator`): en esta fase, sin simulación física todavía, "factible" y "satisface los DesignConstraint conocidos" son la misma pregunta determinista. Documentado explícitamente como punto de extensión para cuando exista Simulation (fase futura): Feasibility se dividirá en un paso propio que sí invoque un simulador.
- **Violaciones HARD bloquean, SOFT no**: un `DesignConstraint` SOFT violado no impide construir el `Design` (queda `VALIDATED`, no `FEASIBLE`) — reutiliza `Priority` de `requirement_contract` para esta distinción, sin duplicar su semántica (sección 13, pedido explícito).
- **`ObjectiveVector.dominates()`**: dominancia de Pareto real (no un score único), pero sin optimizador — es una utilidad de comparación entre dos vectores concretos, no una búsqueda.
- **`integration.py` deliberadamente mínimo**: solo traduce `Design.parameters` (+ `derived_quantities`) a `core.design.schema.Design.parameters`, que es lo único que `core.simulation.engine.run()` necesita leer (verificado leyendo `cold_gas_solver.py:run()`). Traducir `constraints`/`components`/`materials` con fidelidad completa se deja para cuando exista un caso de uso real — no se adelanta diseño especulativo.

## 6. Contratos creados (resumen — detalle completo en DESIGN_DESIGNSPACE_CONTRACT.md)

`Design`, `DesignSpace`, `DesignVariable`, `DesignDomain` (5 tipos),
`DesignRelation`/`CandidateRelation`, `DesignConstraint`,
`DesignObjective`/`ObjectiveVector`, `CandidateDesign`, `DesignGenerator`
(+ 2 implementaciones deterministas), `FeasibilityChecker` (+ 1
implementación estructural), `DesignLineage`, `SearchSpace`,
`NoveltyScorer` (+ 1 implementación heurística), `ExperimentBudget`.

## 7. Tests creados — cobertura por categoría (sección 32)

| Categoría pedida | Archivo(s) | Tests |
|---|---|---|
| Design (creación, serialización, versioning, parent/child, locking) | `test_schema.py`, `test_versioning.py`, `test_locking.py` | 30 |
| Variables (continuous/integer/categorical/boolean/fixed/derived/control) | `test_variables.py` | 22 |
| Domains (límites, válidos, inválidos, unidades) | `test_variables.py` (incluido arriba) | — |
| Relations (válida, dependencia, derivada, inválida/insegura) | `test_relations.py` | 25 |
| Constraints (válidas, conflictos vía feasibility, referencia a Requirement) | `test_constraints.py`, `test_feasibility.py` | 20 |
| Objectives (minimize, maximize, múltiples) | `test_objectives.py` | 9 |
| DesignSpace (válido, incompleto, inconsistente) | `test_design_space.py` | 9 |
| CandidateDesign (válido, inválido, conversión a Design) | `test_candidate.py`, `test_full_flow_integration.py` | 5 |
| Feasibility (factible, no factible) | `test_feasibility.py` | 10 |
| Lineage (parent, child, generation) | `test_lineage.py` | 10 |
| Provenance (7 fuentes) | `test_provenance.py` | 13 |
| Domain independence (sistema genérico, sin vocabulario aeroespacial) | `test_domain_independence.py` | 3 |
| SearchSpace / Generators / Novelty / Budget / Integration | `test_search_space.py`, `test_generators.py`, `test_novelty.py`, `test_budget.py`, `test_integration.py` | 27 |
| **Test de integración completo (sección 33)** | `test_full_flow_integration.py` | 1 (extenso, 9 pasos verificados) |

**Total: 183 tests, 183 pasan.**

## 8. Resultados de tests — antes / después

| Suite | Antes de esta fase | Después de esta fase |
|---|---|---|
| `versions/v01_core` … `v09_advanced_ai` (9 suites) | 1.266 passed | 1.266 passed (sin cambios) |
| `requirement_contract/` | 149 passed | 149 passed (sin cambios) |
| **`design_contract/` (nuevo)** | — | **183 passed** |
| **Total** | **1.415** | **1.598** |

## 9. Import-linter — antes / después

| Paquete | Antes | Después |
|---|---|---|
| v01–v05 | 2/2 | 2/2 (sin cambios) |
| v06–v09 | 3/3 | 3/3 (sin cambios) |
| `requirement_contract/` | 2/2 | 2/2 (sin cambios) |
| **`design_contract/` (nuevo)** | — | **3/3** — incluye un contrato inverso explícito: "requirement_contract no depende de design_contract" (evita que se forme un ciclo entre las dos fases). |

## 10. Demos end-to-end — verificación de no regresión

Re-corrido `run_phase7_8_vertical_slice.py` (v09) tras instalar
`design_contract` en el mismo entorno: resultados numéricos idénticos
byte a byte a las corridas de las dos fases anteriores
(`thrust=0.8644164761965736`, `Isp=76.82536852473885`). El ejemplo
completo de `DESIGN_DESIGNSPACE_CONTRACT.md` se ejecutó literalmente (no
se documentó de memoria) — `estimate_size()==3000` confirmado real.

## 11. Bug real encontrado por el test de integración obligatorio (sección 33)

`GridSweepDesignGenerator` generaba valores continuos con
`np.linspace(...)` sin convertir a `float` nativo de Python (a diferencia
de `core.design.generator.GridSweepGenerator` en v09_advanced_ai, que sí
hace `float(val)` explícitamente). Los `numpy.float64` resultantes
propagaban `numpy.bool_` en las comparaciones del DSL seguro de
`relations.py`, y `DesignConstraint.evaluate()` — correctamente estricto,
exige un `bool` nativo — rechazaba TODOS los resultados como "no
evaluables" (`FeasibilityStatus.UNKNOWN` en vez de `INFEASIBLE`),
ocultando que la restricción de masa derivada del `Requirement` nunca se
estaba aplicando de verdad. El test de integración completo (que corre
generador + relations + constraints juntos, contra un `Requirement` real)
lo detectó inmediatamente; ningún test unitario aislado lo habría
encontrado, porque cada pieza por separado se comportaba "correctamente"
— exactamente el caso que la sección 33 pide cubrir con un test end-to-end
sin mocks. Corregido en `generators/deterministic.py:_axis_values()`
(`float(v) for v in np.linspace(...)`), documentado en el propio código.

## 12. Problemas encontrados (ninguno arquitectónico mayor — sección 40)

No surgió ningún caso que requiriera detenerme a pedir aprobación según
la sección 40 (regla de detención): no fue necesario cambiar `Requirement`,
tocar la arquitectura V01–V09, eliminar nada existente, cambiar contratos
públicos, rehacer el sistema de unidades, conectar `OptimizationAgent`, ni
modificar el orquestador. El único ajuste no trivial fue el bug de la
sección 11 (una corrección interna de tipo de datos, sin implicaciones de
diseño).

## 13. Limitaciones actuales (documentadas, no ocultas)

- `resolve_variable_values()` (pipeline) evalúa las `DesignRelation` en
  una sola pasada — no soporta cadenas de variables DERIVED que dependen
  de OTRAS variables DERIVED (ej. `A` depende de `B` depende de
  variables DESIGN) sin reordenar manualmente la lista de `relations`. Un
  resolvedor topológico completo queda para cuando haya un caso de uso
  real que lo necesite.
- `StructuralFeasibilityChecker` es puramente determinista/estructural —
  no hay ninguna noción de simulación física, tal como pide
  explícitamente la sección 20. La distinción `FEASIBLE` vs. "físicamente
  válido" queda intacta para la fase de Simulation.
- `ParameterDistanceNoveltyScorer` es una heurística de distancia
  euclídea simple, no calibrada estadísticamente — documentado
  explícitamente en el código, mismo espíritu honesto que las
  "confidence" heurísticas ya identificadas en la auditoría original de
  v01–v09.
- Sin persistencia (`DesignRepository`/store) — el versionado/lineage es
  en memoria, igual que `requirement_contract`.
- `to_core_design()` solo traduce `parameters`/`derived_quantities` — no
  `constraints`/`components`/`materials` (ver sección 5, decisión
  deliberada de alcance mínimo).

## 14. Decisiones pendientes

- Cómo (o si) `design_contract.DesignObjective`/`ObjectiveVector` se
  conectan eventualmente con `core.optimization.OptunaOptimizer` — la
  misma pregunta pendiente sobre `OptimizationAgent` de fases anteriores,
  con la que probablemente conviene resolverse junta.
- Cuándo introducir un resolvedor topológico real para `DesignRelation`
  encadenadas (ver limitación de la sección 13).
- Si `design_contract`/`requirement_contract` deberían fusionarse en un
  único paquete de "authoring layer" cuando llegue la fase de
  `EngineeringProblem`, o permanecer separados con `integration.py` como
  puente — no se decide en esta fase.

## 15. Riesgos futuros

- El DSL seguro de expresiones (`relations.py`) es la superficie de mayor
  riesgo de seguridad de todo el proyecto hasta ahora — cualquier
  extensión futura (nuevos tipos de nodo AST permitidos, nuevas funciones
  registradas por defecto) debe revisarse con el mismo estándar que se
  aplicó aquí (denegación por defecto, tests de ataque explícitos).
- Si `EngineeringProblem`/Simulation llegan a necesitar traducir
  `DesignConstraint` con expresiones que el `PhysicsConstraint.evaluate()`
  existente (regex simple) no puede parsear, habrá que decidir si se
  extiende ese evaluador o si `design_contract` expone su propio DSL como
  reemplazo — no se resuelve en esta fase.

---

**Como pediste explícitamente: no continúo hacia Simulation.** Este
informe y `DESIGN_DESIGNSPACE_CONTRACT.md` quedan como entrega final de
esta fase, a la espera de tu revisión.
