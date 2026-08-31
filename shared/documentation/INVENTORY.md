# INVENTARIO DEL PROYECTO

Generado por auditoría antes de la reorganización. Cubre los 159 archivos
del estado final (v09). Agrupado por versión de introducción — cada
archivo aparece en la versión donde se creó y en TODAS las posteriores
(arquitectura acumulativa, no forks paralelos — ver `ARCHITECTURE.md`).

## Resumen por versión

| Versión | Archivos nuevos | Archivos modificados respecto a la anterior | Tests propios |
|---|---|---|---|
| v01_core | 34 | — (base) | 34 |
| v02_knowledge | 16 | `core/models/interfaces.py`, `core/models/ollama_provider.py` (+`embed()`) | +16 |
| v03_physics | 46 | ninguno propio (el archivo `core/physics/interfaces.py` se creó y amplió dentro de la misma v03) | +75 |
| v04_design | 7 | `core/design/schema.py` (+`operating_conditions`, `manufacturing_constraints`, `provenance`) | +18 |
| v05_optimization | 6 | `core/design/engine.py` (refactor: delega en `core/design/candidate.py`), `pyproject.toml` (+extra `optimization`) | +12 |
| v06_agents | 17 | ninguno | +22 |
| v07_propulsion_domain | 3 | ninguno | +9 |
| v08_discovery_report | 5 | ninguno | +10 |
| v09_advanced_ai | 3 | ninguno | +4 |

**Total: 159 archivos, 5 modificaciones cross-versión, 200 tests.**

## Archivos modificados entre versiones (los únicos que requieren atención especial)

Estos 5 archivos NO son estáticos entre versiones — fueron ampliados en
una versión posterior sin romper su forma original. Cada versión
contiene la forma del archivo tal como existía EN ESE MOMENTO (no la
forma final):

| Archivo | Creado en | Modificado en | Qué cambió |
|---|---|---|---|
| `core/models/interfaces.py` | v01 | v02 | + método `embed()` en `ModelProvider` (para Knowledge Engine) |
| `core/models/ollama_provider.py` | v01 | v02 | + implementación de `embed()` vía `/api/embeddings` |
| `core/design/schema.py` | v01 | v04 | + `operating_conditions`, `manufacturing_constraints`, `provenance` en `Design` |
| `core/design/engine.py` | v04 | v05 | refactor: la lógica de construir/validar candidatos se extrajo a `core/design/candidate.py` (nuevo en v05), reutilizada también por el `Optimizer` |
| `pyproject.toml` | v01 | v05 | + `[project.optional-dependencies].optimization` (optuna) |

Verificado explícitamente: NINGUNA otra modificación cross-versión existe.
Todo lo demás introducido en v03, v06, v07, v08, v09 es estrictamente
aditivo (archivos nuevos, cero cambios a archivos de versiones previas).

## Inventario detallado por módulo (dónde vive cada pieza, y desde qué versión)

| Módulo | Ubicación | Versión de origen | ¿Compartido entre versiones? |
|---|---|---|---|
| Requirements Engine | `core/requirements/` | v01 | Sí — usado por todas las versiones posteriores sin cambios |
| Design Representation (schema) | `core/design/schema.py` | v01 (ampliado en v04) | Sí — ver tabla de arriba |
| Design repository (crear/clonar/modificar) | `core/design/repository.py` | v01 | Sí, sin cambios |
| Experiment Store (SQLite) | `core/experiments/` | v01 | Sí, sin cambios |
| Model Registry / ModelProvider | `core/models/` | v01 (ampliado en v02) | Sí — ver tabla de arriba |
| Tool Registry | `core/tools/` | v01 | Sí, sin cambios |
| Orchestrator síncrono (stub steps) | `core/orchestrator/{orchestrator,budget,state,state_machine}.py` | v01 | Sí, sin cambios |
| Dimensional Analysis | `core/validation/dimensional_analysis.py` | v01 | Sí, sin cambios |
| Knowledge Engine (RAG híbrido) | `core/knowledge/` | v02 | Sí — usado por Research Agent (v06) |
| Conocimiento curado (cold-gas thruster) | `domains/satellite/propulsion/knowledge/seed_knowledge.py` | v02 | Sí |
| Physics Engine (interfaces + schemas extendidos) | `core/physics/` | v03 | Sí |
| Numerical Engine (ODE, root-finding, stability) | `core/numerical/` | v03 | Sí |
| Simulation Engine (domain-agnóstico) | `core/simulation/` | v03 | Sí |
| Validation Engine + benchmarks + regression | `core/validation/{schema,engine,benchmark_runner,regression_store}.py` | v03 | Sí |
| PhysicsModel + SimulationSolver del cold-gas thruster | `domains/satellite/propulsion/{physics_models,simulation_adapters}/` | v03 | Sí — es el modelo físico usado en v03-v09 |
| Modelos físicos genéricos (benchmarks del motor) | `core/physics/benchmark_models/` | v03 | Sí |
| Design Space / Design Generator | `core/design/{design_space,generator}.py` | v04 | Sí |
| Design Engine (exploración) | `core/design/engine.py` | v04 (refactor en v05) | Sí — ver tabla de arriba |
| Lógica compartida de candidatos | `core/design/candidate.py` | v05 | Sí — usado por Design Engine (v04) y Optimizer (v05) |
| Optimization Engine (Optuna) | `core/optimization/` | v05 | Sí |
| Agentes (Research/Design/Simulation/Analysis/Critic/Optimization) | `agents/` | v06 | Sí — usado por Report Generator indirectamente vía Experiment Store |
| Domain Pack formalizado (Requirements builder) | `domains/satellite/propulsion/{requirements_schema,evaluation_metrics}.py` | v07 | Sí |
| Report Generator | `core/orchestrator/report.py` | v08 | Sí |
| Discovery/Optimization Mode | `core/orchestrator/discovery.py` | v08 | Sí |
| Interfaces de ML (sin implementar) | `core/ml/surrogate.py` | v09 | N/A (no usado por nada aún — es preparación) |

## Componentes NO movidos a `shared/`

`shared/` quedó deliberadamente casi vacío de código. Razón: en una
arquitectura acumulativa (no forks paralelos), prácticamente todo el
`core/` "compartido" entre v04 y v09, por ejemplo, es en realidad el
`core/` de v04 evolucionando — no son dos copias idénticas de un mismo
archivo estático. Intentar extraer un `shared/core/` real habría
implicado reescribir las importaciones de las 9 versiones para apuntar
a una ubicación externa, con alto riesgo de romper algo — exactamente lo
que las reglas de esta tarea prohíben. Ver `ARCHITECTURE.md` para el
razonamiento completo.

Lo que SÍ es genuinamente estático y compartible sin riesgo:
- `shared/documentation/`: este inventario, y referencias cruzadas.
- El propio `ARCHITECTURE.md` y `versions/VERSION_MAP.md` (documentación, no código).
