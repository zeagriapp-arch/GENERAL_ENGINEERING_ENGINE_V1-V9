# v06_agents

## Qué contiene

Todo lo de v05_optimization, más el **Agent Orchestrator**:
- 6 agentes especializados (`agents/`): `ResearchAgent`, `DesignAgent`, `SimulationAgent`, `AnalysisAgent`, `CriticAgent`, `OptimizationAgent` — sobre el `ModelProvider`/Tool Registry de v01.
- `AsyncOrchestrator` (`agents/orchestrator.py` — deliberadamente NO en `core/`, porque importa agentes y `core` nunca puede importar `agents`).

## Capacidades — y la garantía de seguridad más importante del proyecto

El LLM propone, nunca decide la física ni la validación:
- `DesignAgent` propone valores, pero se validan contra bounds ANTES de construir el `Design` — una propuesta fuera de rango nunca llega al solver.
- `CriticAgent` calcula el veredicto ACCEPT/REJECT con la MISMA regla determinista que usan `DesignEngine` (v04) y `Optimizer` (v05), ANTES de preguntarle nada al LLM. El LLM solo puede añadir hallazgos cualitativos — probado explícitamente: un Critic LLM "optimista" no puede convertir un REJECT físico en ACCEPT.
- `AnalysisAgent` separa cálculo (determinista) de narrativa (LLM) — los deltas numéricos nunca salen del LLM.

## Qué cambió respecto a v05_optimization

Todo aditivo — ningún archivo de v01-v05 se modificó.

## Cómo ejecutarla

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,optimization]"
pytest -q                                    # 177 tests
python scripts/run_phase6_vertical_slice.py  # ciclo completo con agentes guionizados
```

## Dependencias

Mismas que v05_optimization — sin dependencias nuevas de terceros.

## Tests disponibles

177 tests (155 heredados + 22 nuevos: 6 archivos de tests de agentes + 1 de integración end-to-end).

## Limitaciones conocidas

- **No hay servidor Ollama disponible en el entorno donde se desarrolló
  esta versión.** Todos los tests (y el script de demo) usan un
  `ModelProvider` con respuestas guionizadas (`ScriptedModelProvider`),
  no un LLM real. `OllamaProvider` (v01) está implementado pero nunca se
  ha ejercitado contra un servidor Ollama real — eso requiere
  validación local por parte de quien despliegue el proyecto.
- El `OptimizationAgent` sugiere foco de búsqueda pero no está
  conectado al loop principal del `AsyncOrchestrator` — existe y tiene
  tests propios, pero la integración completa (LLM sugiriendo foco →
  Optimizer usándolo para acotar el espacio) no se implementó en V1.

## Dependencia de versiones anteriores

Depende de v01-v05 (incluidas en esta carpeta). Se ejecuta de forma
independiente.
