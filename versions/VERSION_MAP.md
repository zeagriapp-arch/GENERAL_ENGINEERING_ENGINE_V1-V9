# VERSION MAP

Qué construye/añade cada versión, en una línea por versión + detalle.
Ver `ARCHITECTURE.md` (raíz) para el porqué de la estructura acumulativa.

---

## v01_core — El núcleo, sin conocimiento ni física todavía

**Construye:** Requirements Engine (validación dimensional obligatoria),
Design Representation, Experiment Store (SQLite, con grafo de
experimentos), Model Registry + `OllamaProvider`, Tool Registry (permisos
por agente aplicados en runtime), Orchestrator síncrono con Budget
anti-loop-infinito.

**Principio ya presente desde aquí:** sin PhysicsModel todavía, el
sistema se detiene explícitamente en `INSUFFICIENT_EVIDENCE` en vez de
inventar un resultado.

---

## v02_knowledge — Añade: Knowledge Engine

**Añade sobre v01:** RAG híbrido (vector search + capa estructurada +
provenance), 6 fuentes públicas curadas (NASA Glenn Research Center,
Wikipedia) sobre ecuaciones de tobera ideal, `search_knowledge()` con
trazabilidad completa hasta la fuente original.

**Modifica de v01:** `ModelProvider` gana el método `embed()`.

---

## v03_physics — Añade: Physics + Numerical + Simulation + Validation Engines

**Añade sobre v02:** `PhysicsModel`/`SimulationSolver` del cold-gas
thruster (tobera ideal, flujo isentrópico), Numerical Engine (ODE vía
SciPy, root-finding), Validation Engine con `ValidationReport`,
`BenchmarkCase` + regression testing, 2 modelos físicos genéricos
(caída libre, oscilador masa-resorte) para validar el motor en sí mismo
sin atarlo al dominio satelital.

**No modifica nada de v01/v02.**

---

## v04_design — Añade: Design Engine

**Añade sobre v03:** `DesignSpace`/`DesignVariable` (bounds explícitos
derivados de Requirements), `DesignGenerator` (grid sweep + random
sampling, intercambiables), `DesignEngine.explore()`: genera candidatos
→ simula con física real → valida constraints → PASS/FAIL con razones.

**Modifica de v01:** `Design` gana `operating_conditions`,
`manufacturing_constraints`, `provenance`.

---

## v05_optimization — Añade: Optimization Engine

**Añade sobre v04:** `Optimizer` + `OptunaOptimizer` (TPE sampler),
single/multi-objective (Pareto front), poda explícita de candidatos
inválidos (`optuna.TrialPruned()`, nunca un valor inventado).

**Modifica de v04:** `DesignEngine` se refactoriza para delegar la
lógica de candidatos en el nuevo `core/design/candidate.py`, compartido
también por el Optimizer (elimina duplicación).

---

## v06_agents — Añade: Agent Orchestrator

**Añade sobre v05:** 6 agentes especializados (Research, Design,
Simulation, Analysis, Critic, Optimization) sobre `ModelProvider`/Tool
Registry; `AsyncOrchestrator`. Verificado explícitamente: un Critic
Agent (LLM) "optimista" no puede convertir un veredicto físicamente
REJECT en ACCEPT — la decisión se calcula antes de preguntarle al modelo.

**No modifica nada de versiones previas.**

**Nota:** sin servidor Ollama disponible en el entorno de desarrollo,
todos los tests usan un `ModelProvider` con respuestas guionizadas.

---

## v07_propulsion_domain — Añade: Domain Pack formalizado

**Añade sobre v06:** `build_cold_gas_requirements()` (consolida los 7
parámetros antes duplicados en 4 scripts de demo distintos),
`evaluation_metrics.py` (eficiencia vs. Isp teórico, deltas porcentuales
contra baseline).

**No modifica nada de versiones previas.**

---

## v08_discovery_report — Añade: Report Generator + Discovery Mode

**Añade sobre v07:** `generate_report()` — responde determinísticamente
(sin LLM) las 12 preguntas de "Definition of Done" (qué diseño, qué
cambió y por qué, qué modelo, qué supuestos, qué simulación, qué
resultado, qué incertidumbre, qué constraints, qué fuentes, qué
experimentos previos influyeron, si es reproducible). `run_discovery_mode()`
conecta Design Space + Optimizer + Experiment Store + Report en un solo
ciclo, persistiendo CADA candidato evaluado.

**No modifica nada de versiones previas.**

---

## v09_advanced_ai — Añade: interfaces de Scientific ML (sin implementar)

**Añade sobre v08:** `SurrogateModel`/`ActiveLearningStrategy` — solo
interfaces, documentando el pipeline previsto (Physical Simulator →
Dataset → ML Surrogate → Fast Prediction → Candidate Filtering →
Physical Simulation Validation) y el principio no negociable: un
surrogate nunca sustituye al simulador físico sin validación.

**No modifica nada de versiones previas.** Decisión deliberada de NO
implementar Phase 9 real en V1 — evitar sobre-ingeniería.

---

## Resumen numérico

| Versión | Tests propios | Archivos totales |
|---|---|---|
| v01_core | 34 | 58 |
| v02_knowledge | 50 | 69 |
| v03_physics | 125 | 115 |
| v04_design | 143 | 122 |
| v05_optimization | 155 | 129 |
| v06_agents | 177 | 148 |
| v07_propulsion_domain | 186 | 151 |
| v08_discovery_report | 196 | 156 |
| v09_advanced_ai | 200 | 159 |

Todos los tests de cada fila fueron corridos y pasan de forma aislada
(ver `shared/documentation/INVENTORY.md` para el detalle de validación).
