# DESIGN_DESIGNSPACE_CONTRACT.md

Documentación del contrato implementado en `design_contract/` (raíz del
repositorio, fuera de `versions/` — depende de `versions/v09_advanced_ai`
y de `requirement_contract` como paquetes, no como copias; ver
`design_contract/README.md`).

---

## Separación fundamental: Requirement vs. DesignSpace vs. Design

```
Requirement          "¿qué debe cumplir el sistema?"       mass <= 20 kg
        │
        ▼
DesignSpace           "¿qué soluciones podemos explorar?"   diameter ∈ [0.10, 0.50] m
        │                                                    length ∈ [0.20, 1.00] m
        │                                                    material ∈ {A, B, C}
        ▼
Design                "una solución concreta"                diameter = 0.237 m
                                                               length = 0.641 m
                                                               material = B
```

Un `DesignSpace` referencia los `Requirement` que intenta satisfacer por
**id** (`DesignSpace.requirement_ids: list[str]`) — nunca duplica su
contenido. Un `DesignConstraint` puede referenciar un `Requirement` del
que deriva (`DesignConstraint.requirement_id`), pero es un concepto
distinto: el `Requirement` es la fuente de verdad sobre el sistema
completo; el `DesignConstraint` es lo necesario para que el espacio de
diseño tenga sentido (puede no tener ningún `Requirement` detrás — ej.
`thickness >= minimum_thickness(diameter)` es puramente geométrico).

---

## 1. Design

Solución concreta de ingeniería, independiente de dominio.

```python
class Design:
    id, version, name, description, parent_design_id       # identidad + linaje de VERSIÓN
    architecture: Architecture
    components: list[Component]
    geometry: Optional[Geometry]
    materials: list[Material]
    parameters: dict[str, Value]              # valores fijos/resueltos
    variables: dict[str, DesignVariable]        # con su rol/dominio
    derived_quantities: dict[str, Value]         # calculadas vía DesignRelation
    interfaces: list[ComponentInterface]
    operating_conditions: dict[str, Value]
    assumptions: list[str]
    constraints: list[DesignConstraint]
    provenance: DesignProvenance
    status: DesignStatus
    metadata: dict
```

Se construye SIEMPRE a través de `DesignValidationPipeline` a partir de un
`CandidateDesign` — nunca directamente por el LLM.

## 2. DesignSpace

```python
class DesignSpace:
    id, name
    variables: dict[str, DesignVariable]
    relations: list[DesignRelation]
    constraints: list[DesignConstraint]
    objectives: list[DesignObjective]
    requirement_ids: list[str]           # qué Requirements intenta satisfacer
    provenance: DesignProvenance
    status: DesignSpaceStatus            # DRAFT | VALID | INCOMPLETE | INCONSISTENT
```

`estimate_size()` da una estimación de cardinalidad (el "10^12" del
ejemplo de la especificación) — CONTINUOUS se discretiza a una resolución
configurable (10 puntos por defecto) para el cálculo, ya que un espacio
continuo real es no numerable; es una estimación de orden de magnitud, no
un conteo exacto. `validate_internal_consistency()` detecta: variables
DERIVED sin relación que las calcule, relations/constraints que
referencian variables inexistentes.

## 3. DesignVariable / DesignDomain

```python
class VariableRole(Enum): DESIGN, FIXED, DERIVED, CONTROL
class DesignDomainType(Enum): CONTINUOUS, INTEGER, DISCRETE, BOOLEAN, CATEGORICAL

class DesignDomain:
    kind: DesignDomainType
    lower_bound, upper_bound: float | None   # CONTINUOUS/INTEGER
    allowed_values: list | None                # DISCRETE/CATEGORICAL/BOOLEAN

class DesignVariable:
    id, name, role: VariableRole, domain: DesignDomain, unit, provenance
    type -> domain.kind   # propiedad de solo lectura, no un campo separado
```

Generaliza `core.design.design_space.DesignVariable` (v09_advanced_ai,
solo continuo) a los 5 tipos de dominio de la especificación. Ejemplo:

```python
diameter = DesignVariable(name="diameter", role=DESIGN,
                           domain=DesignDomain.continuous(0.10, 0.50), unit="m", ...)
material = DesignVariable(name="material", role=DESIGN,
                           domain=DesignDomain.categorical(["A","B","C"]), ...)
```

## 4. DesignRelation / CandidateRelation — el DSL seguro

`volume = f(radius, length)`: una variable DERIVED nunca se propone
directamente, se calcula. El LLM puede proponer una `CandidateRelation`,
pero **nunca ejecuta código** — el flujo es:

```
CandidateRelation -> validate_candidate_relation() -> DesignRelation
```

Seguridad (sección 31 — la regla más estricta de esta fase):
`design_contract.relations` recorre el AST de la expresión
(`ast.parse(expr, mode="eval")`) con **denegación por defecto**: cada
tipo de nodo necesita un `visit_*` explícito o se rechaza. Nunca hay
`eval()`/`exec()`. Solo se permiten literales numéricos, nombres de
variable del namespace provisto, operadores aritméticos/de comparación, y
llamadas a funciones por nombre simple registradas explícitamente
(`register_relation_function()`). Atributos (`obj.attr`), subíndices
(`obj[i]`), lambdas, comprensiones, imports, f-strings — rechazados
automáticamente por no tener un `visit_*`, sin necesitar una lista negra.

Verificado con 11 expresiones de ataque reales en los tests
(`__import__('os').system(...)`, `open(...)`, `().__class__.__bases__[0]`,
etc.) — todas rechazadas.

## 5. DesignConstraint

```python
class DesignConstraint:
    id, name, expression: str, priority: Priority   # reutiliza HARD/SOFT de requirement_contract
    requirement_id: Optional[str]                     # referencia explícita, nunca duplica contenido
    provenance: DesignProvenance
```

Evaluado con el mismo DSL seguro de `DesignRelation`. Ejemplo:
`thickness >= minimum_thickness(diameter)`,
`component_a_mass + component_b_mass <= total_mass`.

## 6. DesignObjective / ObjectiveVector

```python
class DesignObjective:
    name, direction: MINIMIZE|MAXIMIZE, metric, weight (opcional), priority (opcional)

class ObjectiveVector:
    values: dict[str, float]     # nunca colapsado a un único score
    def dominates(other, objectives) -> bool   # dominancia de Pareto — sin optimizador Pareto todavía
```

## 7. CandidateDesign

Sin `id`/`version`/`status` propios — mismo principio que
`RequirementCandidate`: una propuesta no tiene la autoridad de un
`Design` hasta pasar la pipeline.

```
CandidateDesign -> SchemaValidator -> StructuralValidator -> UnitValidator
                 -> ConstraintValidator (= Constraint validation + Feasibility)
                 -> Design
```

## 8. Feasibility

`FEASIBLE` nunca se confunde con "simulado": `StructuralFeasibilityChecker`
solo hace checks deterministas (dominio de cada variable + evaluación de
`DesignConstraint`, calculando `DesignRelation` cuando hace falta) — nunca
invoca un simulador físico.

```
Candidate -> Structural feasibility (ESTA FASE) -> Physics simulation (FUTURO) -> Physical feasibility
```

`FeasibilityStatus`: `FEASIBLE` | `INFEASIBLE` | `UNKNOWN` (datos
insuficientes para evaluar — nunca se confunde con "no factible").

## 9. SearchSpace

Distinto de `DesignSpace`: la región que un algoritmo decide explorar
realmente. `SearchSpace.restricts(design_space)` verifica que nunca
amplíe los bounds del `DesignSpace` de origen — solo puede acotar.

```
DesignSpace: 10^12 combinaciones posibles  (estimate_size())
SearchSpace: 10^6 candidatos seleccionados  (max_candidates)
```

`SearchStrategyKind`: `GRID`, `RANDOM`, `LATIN_HYPERCUBE`, `BAYESIAN`,
`EVOLUTIONARY`, `ADAPTIVE`, `LLM_GUIDED`, `HYBRID` — vocabulario
extensible, solo GRID/RANDOM tienen generador implementado en esta fase.

## 10. DesignGenerator

```python
class DesignGenerator(ABC):
    def generate(self, design_space, *, n, seed) -> list[CandidateDesign]: ...
```

Implementaciones de esta fase: `GridSweepDesignGenerator`,
`RandomSamplingDesignGenerator` — generalizan
`core.design.generator.{GridSweepGenerator, RandomSamplingGenerator}`
(v09_advanced_ai) a los 5 tipos de dominio. `GeneratorKind` (extensible):
`PARAMETER`, `RULE_BASED`, `COMBINATORIAL`, `EVOLUTIONARY`,
`LLM_PROPOSAL`, `HYBRID`.

## 11. Lineage

Linaje de **generación** (qué Design produjo qué otro, vía qué
transformación) — distinto del linaje de **versión**
(`Design.parent_design_id`, sección 14).

```
             Design A
             /      \
       Design B    Design C
          |
       Design D
```

```python
lineage = DesignLineage()
lineage = lineage.record(parent_id="A", child_id="B", transformation="mutation")
lineage.generation_of("D")  # -> 2
```

## 12. Provenance

`DesignProvenanceSource`: `USER`, `GENERATED`, `IMPORTED`, `DERIVED`,
`OPTIMIZED`, `LLM_PROPOSED`, `SYSTEM` — vocabulario **procedimental**
(cómo se produjo el diseño), deliberadamente distinto del vocabulario
**epistémico** de `requirement_contract.schema.ProvenanceSource`
(`USER`/`DOCUMENT`/`COMPUTED`/`ASSUMPTION`/`SYSTEM`, de dónde salió una
afirmación) — no tendría sentido "DOCUMENT" para explicar cómo se generó
un diseño, ni "OPTIMIZED" para una afirmación numérica.

## 13. Versioning

Mismo patrón exacto que `requirement_contract.versioning` (modelado sobre
`core.design.repository.clone()`/`modify()`): `lock()` (solo desde
`FEASIBLE`, nunca muta) y `revise()` (produce un Design nuevo,
`version + 1`, `parent_design_id` enlazado, `status` reiniciado a
`DRAFT`). D001 v1 → v2 → v3, el historial se preserva siempre.

## 14. Novelty

`NoveltyScorer` — interfaz limpia, sin sistema de embeddings (diferido
explícitamente). Única implementación: `ParameterDistanceNoveltyScorer`
(distancia euclídea normalizada sobre parámetros numéricos compartidos —
heurística simple y determinista, documentada como tal, mismo espíritu
que `HashingEmbedder` en v09_advanced_ai). `Novelty` nunca se mezcla con
`Performance`/`Feasibility` en un solo score.

## 15. Integración LLM futura

```
LLM -> Proposal -> Deterministic Validation -> Candidate -> Feasibility -> Simulation
```

Nunca: `LLM -> "esto funciona"`. El LLM puede producir un
`RequirementCandidate`, un `CandidateRelation`, o (en una fase futura) un
`CandidateDesign` completo — en los tres casos, pasa por una pipeline
determinista antes de tener cualquier autoridad. `RequirementCandidate`/
`CandidateRelation`/`CandidateDesign` son, deliberadamente, `pydantic.BaseModel`
normales — el mismo tipo de objeto que ya se usa como `response_schema=`
en `core.models.interfaces.ModelProvider.complete()` — sin acoplarse a
Ollama/OpenAI/Claude/Gemini en ningún punto de este contrato.

---

## Ejemplo completo (el de la especificación)

```python
from design_contract.variables import DesignDomain, DesignVariable, VariableRole
from design_contract.design_space import DesignSpace
from design_contract.generators.deterministic import GridSweepDesignGenerator
from design_contract.validators.pipeline import DesignValidationPipeline
from design_contract.versioning import lock

variables = {
    "diameter": DesignVariable(name="diameter", role=VariableRole.DESIGN,
                                domain=DesignDomain.continuous(0.10, 0.50), unit="m", provenance=...),
    "length": DesignVariable(name="length", role=VariableRole.DESIGN,
                              domain=DesignDomain.continuous(0.20, 1.00), unit="m", provenance=...),
    "thickness": DesignVariable(name="thickness", role=VariableRole.DESIGN,
                                 domain=DesignDomain.continuous(0.001, 0.010), unit="m", provenance=...),
    "material": DesignVariable(name="material", role=VariableRole.DESIGN,
                                domain=DesignDomain.categorical(["A", "B", "C"]), provenance=...),
}
space = DesignSpace(name="cylinder-space", variables=variables, provenance=...)
print(space.estimate_size())   # 3000 (orden de magnitud, resolución 10 por continua)

candidates = GridSweepDesignGenerator().generate(space, n=10, seed=42)
# Candidate 001, Candidate 002, Candidate 003, ...

pipeline = DesignValidationPipeline(space)
valid = [d for c in candidates if (d := pipeline.run(c)[0]) is not None]
# El sistema determina cuáles cumplen las reglas estructurales — antes de
# enviar nada a Simulation (fase futura, sin implementar aquí).

locked = lock(valid[0])   # status == LOCKED
```

Ver `tests/test_full_flow_integration.py` para el flujo completo real
(Requirement → DesignSpace → Variables → Relations → Constraints →
CandidateGenerator → CandidateDesign → Feasibility → Design), ejecutado
sin mocks — incluye un `Requirement` real de `requirement_contract`
restringiendo el resultado.

---

## Qué NO cubre esta fase

Simulation, Evaluation, Optimization reales; CFD/FEA/CAD; integración de
`OptimizationAgent`; algoritmos Bayesian/evolutivos/Pareto completos;
sistema de embeddings para Novelty; persistencia (`DesignRepository`/store).
Ver `DESIGN_DESIGNSPACE_IMPLEMENTATION_REPORT.md` sección de limitaciones
para el detalle completo.
