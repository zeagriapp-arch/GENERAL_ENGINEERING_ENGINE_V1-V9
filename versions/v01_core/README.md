# v01_core

## Qué contiene

El núcleo del motor, sin conocimiento de dominio ni física todavía:
- **Requirements Engine**: convierte un problema en `Requirements` estructurado, con gate dimensional obligatorio (`pint`).
- **Design Representation**: schema universal de `Design` (components, geometry, materials, parameters, interfaces, constraints, objectives).
- **Experiment Store**: SQLite, inmutable tras cierre (ACCEPTED/REJECTED no se puede resobrescribir), reconstrucción de grafo de experimentos.
- **Model Registry + `OllamaProvider`**: abstracción sobre el LLM, nada de negocio hardcodea nombres de modelo.
- **Tool Registry**: permisos por agente aplicados en runtime (no solo convención de prompt).
- **Orchestrator síncrono**: loop RESEARCH→DESIGN→SIMULATE→ANALYZE→CRITIQUE con `Budget` anti-loop-infinito.

## Capacidades

Puede ejecutar el ciclo completo Requirements → Design → Experiment
guardado/recuperado. **Sin PhysicsModel todavía** — el `Orchestrator` se
detiene explícitamente en `INSUFFICIENT_EVIDENCE` en vez de inventar un
resultado (Principio Fundamental del proyecto, presente desde esta
primera versión).

## Qué cambió respecto a la versión anterior

N/A — es la primera versión.

## Cómo ejecutarla

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                    # 34 tests
lint-imports                                 # reglas de arquitectura
python scripts/run_first_experiment.py       # vertical slice
```

## Dependencias

`pydantic`, `pydantic-settings`, `pyyaml`, `pint`, `numpy`, `scipy`,
`structlog`, `httpx`. Dev: `pytest`, `pytest-asyncio`, `hypothesis`,
`import-linter`.

## Tests disponibles

34 tests (`tests/unit/` + `tests/integration/`), todos pasan de forma
aislada.

## Limitaciones conocidas

- `config/tools.yaml` y `config/models.yaml` ya anticipan handlers de
  fases futuras (`search_knowledge`, `run_simulation`, `run_optimizer`,
  etc.) que aún no existen como módulos — invocarlos devuelve un error
  explícito manejado (`ToolResult(ok=False, ...)`), no un crash. Es
  diseño intencional (forward declaration), no un bug.
- Sin Knowledge Engine, Physics Engine, ni agentes LLM reales todavía.
- `OllamaProvider` no tiene `embed()` en esta versión (llega en v02).

## Dependencia de versiones anteriores

Ninguna — es la base. Se ejecuta de forma completamente independiente.
