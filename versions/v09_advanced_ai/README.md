# v09_advanced_ai

## Qué contiene

Todo lo de v08_discovery_report, más las **interfaces de Scientific
Machine Learning** (sin implementación — decisión deliberada):
- `core/ml/surrogate.py`: `SurrogateModel` (ABC: `fit()`/`predict()`) y `ActiveLearningStrategy` (ABC: `suggest_next_points()`).
- Documenta el pipeline previsto: `Physical Simulator → Dataset → ML Surrogate → Fast Prediction → Candidate Filtering → Physical Simulation Validation`.
- Principio no negociable codificado en el docstring: un surrogate NUNCA sustituye al simulador físico sin validación.

## Capacidades

Ninguna capacidad de ML real — son interfaces que garantizan que,
cuando se implemente un surrogate en el futuro, se integrará con la
misma disciplina que el resto del sistema (nunca reemplaza al validador
físico), sin tener que rediseñar nada del `core` existente.

## Qué cambió respecto a v08_discovery_report

Todo aditivo — ningún archivo de v01-v08 se modificó. Es la versión
final del proyecto (V1 completo).

## Cómo ejecutarla

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,optimization]"
pytest -q                                       # 200 tests
lint-imports                                    # reglas de arquitectura, las 9 fases
python scripts/run_phase7_8_vertical_slice.py   # vertical slice completo
```

## Dependencias

Mismas que v08_discovery_report — sin dependencias nuevas de terceros.

## Tests disponibles

200 tests (196 heredados + 4 nuevos: `test_ml_interfaces.py`, verifica
que las ABC no se pueden instanciar sin implementar ambos métodos).

## Limitaciones conocidas — resumen de todo el proyecto V1

- Sin servidor Ollama real ejercitado (ver v06).
- Un solo `PhysicsModel` por dominio; un solo Domain Pack (`satellite.propulsion`).
- Vector Store simplificado (coseno sobre SQLite, no Chroma real — ver v02).
- `SensitivityAnalyzer`/`ExecutionBackend`/`SurrogateModel`: interfaces sin implementación (deliberado).
- `OptimizationAgent` no conectado al loop principal del Orchestrator (ver v06).
- El ciclo Discovery Mode / Optimization Mode aún comparte implementación (ver v08).

## Dependencia de versiones anteriores

Depende de v01-v08 (incluidas en esta carpeta). Se ejecuta de forma
independiente. Es el estado final y más completo del proyecto — para
uso en producción o desarrollo continuo, esta es la versión de partida.
