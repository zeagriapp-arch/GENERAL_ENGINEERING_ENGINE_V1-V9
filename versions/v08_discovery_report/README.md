# v08_discovery_report

## Qué contiene

Todo lo de v07_propulsion_domain, más el **Report Generator** y
**Discovery/Optimization Mode**:
- `core/orchestrator/report.py`: `generate_report()` — función pura y determinista (SIN LLM) que responde las 12 preguntas de "Definition of Done for V1": qué diseño se evaluó, qué variables cambiaron y por qué, qué modelo se usó, qué supuestos, qué simulación, qué resultado, qué incertidumbre, qué constraints se satisficieron/violaron, qué fuentes respaldan los datos, qué experimentos previos influyeron, y si es reproducible.
- `core/orchestrator/discovery.py`: `run_discovery_mode()` conecta `DesignSpace` (v04) + `Optimizer` (v05) + `ExperimentStore` (v01) + Report Generator en un solo ciclo ejecutable — persiste CADA candidato evaluado (no solo el mejor), y si ninguno tiene evidencia suficiente devuelve `report=None` en vez de inventar un ganador.

## Capacidades

Es el primer punto del proyecto donde el sistema puede **explicarse a sí
mismo** completamente, con datos reales y sin depender de que un LLM
narre honestamente los resultados.

## Qué cambió respecto a v07_propulsion_domain

Todo aditivo — ningún archivo de v01-v07 se modificó.

## Cómo ejecutarla

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,optimization]"
pytest -q                                       # 196 tests
python scripts/run_phase7_8_vertical_slice.py   # ciclo completo + Report con las 12 preguntas
```

## Dependencias

Mismas que v07_propulsion_domain — sin dependencias nuevas.

## Tests disponibles

196 tests (186 heredados + 10 nuevos: `test_report_generator.py` + `test_discovery_mode.py`).

## Limitaciones conocidas

- `generate_report()` identifica el modelo físico usado consultando el
  `SimulationSolver` registrado en `core.simulation.engine` EN EL
  MOMENTO de generar el reporte — si se genera el reporte sin haber
  llamado `bootstrap()` primero, `model_used` queda como `"unknown"` y
  `reproducible=False` (comportamiento honesto, no un bug).
- Discovery Mode y Optimization Mode comparten la misma implementación
  en V1 (decisión documentada en `ARCHITECTURE.md` del proyecto
  original) — la diferencia real entre "explorar arquitecturas
  alternativas" y "afinar una ya elegida" solo aparecerá cuando haya
  más de un `PhysicsModel` por dominio.

## Dependencia de versiones anteriores

Depende de v01-v07 (incluidas en esta carpeta). Se ejecuta de forma
independiente.
