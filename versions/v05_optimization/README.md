# v05_optimization

## Qué contiene

Todo lo de v04_design, más el **Optimization Engine**:
- `Optimizer` (interfaz) + `OptunaOptimizer`: TPE sampler real de Optuna, sin sustituir el optimizer por un LLM.
- Soporte single-objective y multi-objective (Pareto front vía `study.best_trials`) sin lógica distinta para cada caso.
- Candidatos físicamente inválidos o que violan un constraint duro se podan explícitamente (`optuna.TrialPruned()`) — nunca se le pasa a Optuna un valor objetivo inventado.
- `core/design/candidate.py`: lógica compartida de construir/validar un candidato, extraída de `DesignEngine` (v04) para que Optimizer no la duplique.

## Capacidades

Búsqueda matemática dirigida, no solo exploración. Con una variable y
relación monótona converge al mismo óptimo que el grid sweep de v04;
con más dimensiones (no ejercitado en el vertical slice, pero soportado
por el mismo `DesignSpace`) la ventaja de la búsqueda dirigida crece.

## Qué cambió respecto a v04_design

- **Nuevo**: `core/design/candidate.py`, `core/optimization/`.
- **Modificado**: `core/design/engine.py` se refactoriza para delegar en `core/design/candidate.py` (mismo comportamiento externo, código no duplicado). `pyproject.toml` gana el extra `[project.optional-dependencies].optimization` (optuna).

## Cómo ejecutarla

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,optimization]"
pytest -q                                    # 155 tests
python scripts/run_phase5_vertical_slice.py  # compara grid sweep (v04) vs Optuna
```

## Dependencias

Añade `optuna>=3.6` (extra `optimization`).

## Tests disponibles

155 tests (143 heredados + 12 nuevos: `test_design_candidate.py` +
`test_optuna_optimizer.py`).

## Limitaciones conocidas

- El `OptimizationAgent` que sugiere "qué variables explorar" no llega
  hasta v06 — en esta versión el Optimizer decide solo, sin ningún
  input de un LLM.
- No se implementó optimización evolutiva ni Bayesiana más allá de lo
  que Optuna trae por defecto (TPE) — suficiente para V1.

## Dependencia de versiones anteriores

Depende de v01-v04 (incluidas en esta carpeta). Se ejecuta de forma
independiente.
