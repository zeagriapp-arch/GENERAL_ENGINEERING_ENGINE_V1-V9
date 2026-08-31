# v07_propulsion_domain

## Qué contiene

Todo lo de v06_agents, más la **formalización del Domain Pack**:
- `domains/satellite/propulsion/requirements_schema.py`: `build_cold_gas_requirements()` consolida los 7 parámetros del cold-gas thruster que estaban duplicados en 4 scripts de demo distintos (v03-v06).
- `domains/satellite/propulsion/evaluation_metrics.py`: métricas específicas del dominio — eficiencia vs. Isp teórico máximo, comparación porcentual de deltas contra un baseline.

## Capacidades

Ninguna capacidad nueva del motor — es refactorización/consolidación de
lo que ya existía, para que scripts y tests futuros no dupliquen los
mismos 7 parámetros una y otra vez.

## Qué cambió respecto a v06_agents

Todo aditivo — ningún archivo de v01-v06 se modificó.

## Cómo ejecutarla

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,optimization]"
pytest -q                                    # 186 tests
python scripts/run_phase6_vertical_slice.py  # (Phase 8 aún no existe en esta versión)
```

## Dependencias

Mismas que v06_agents — sin dependencias nuevas.

## Tests disponibles

186 tests (177 heredados + 9 nuevos: `test_domain_pack_propulsion.py`).

## Limitaciones conocidas

- Solo formaliza el dominio `satellite.propulsion` — no hay Domain Pack
  para ningún otro subsistema (estructuras, térmico, potencia, etc.),
  tal como pide la spec original para V1 (un solo dominio, extensible).

## Dependencia de versiones anteriores

Depende de v01-v06 (incluidas en esta carpeta). Se ejecuta de forma
independiente.
