# v03_physics

## Qué contiene

Todo lo de v02_knowledge, más **Physics + Numerical + Simulation +
Validation Engines**:
- `PhysicsModel`/`SimulationSolver` del cold-gas thruster (tobera ideal, flujo isentrópico 1-D) — las 6 ecuaciones curadas en v02, ahora ejecutables.
- Numerical Engine: `ODESolver` (SciPy `solve_ivp`), root-finding generalizado, `SolverRegistry`, detección de inestabilidad (NaN/Inf).
- `Variable`/`Parameter`/`Assumption`/`PhysicsConstraint` (con estado SATISFIED/VIOLATED/**UNKNOWN** — nunca asume satisfecho por falta de datos).
- `ValidationEngine` + `ValidationReport`, `BenchmarkCase` + regression testing.
- **2 modelos físicos genéricos** (`core/physics/benchmark_models/`): caída libre algebraica + oscilador masa-resorte (ODE) — validan el motor en sí mismo, sin atarlo al dominio satelital.
- Benchmarks de V&V del cold-gas thruster: identidades algebraicas exactas (Isp, continuidad de masa, round-trip Mach-área).

## Capacidades

Primera versión con física real: puede simular, no solo proponer.
Resultados físicamente coherentes (Isp de N2 en 60-90s, orden de magnitud correcto de literatura).

## Qué cambió respecto a v02_knowledge

Todo aditivo — ningún archivo de v01/v02 se modificó. `core/physics/interfaces.py`
se creó y se amplió DENTRO de esta misma versión (dos rondas de trabajo
sobre la misma spec, sin cruzar el límite de versión).

## Cómo ejecutarla

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                    # 125 tests
lint-imports
python scripts/run_phase3_vertical_slice.py  # barrido de área de tobera con física real
```

## Dependencias

Mismas que v02_knowledge (no se añadió ninguna nueva — SciPy ya estaba
desde v01 para el Numerical Engine).

## Tests disponibles

125 tests. Incluye `tests/benchmarks/` con 2 archivos de V&V (identidad
algebraica del cold-gas thruster + benchmarks genéricos con solución
analítica exacta).

## Limitaciones conocidas

- Un solo PhysicsModel por dominio (`satellite.propulsion` → cold-gas
  thruster). El registro (`PhysicsModelRegistry`/`core.simulation.engine`)
  soporta más, pero no se implementó ningún segundo modelo en V1.
- `SensitivityAnalyzer`/`ExecutionBackend`: interfaces preparadas, sin
  implementación (decisión deliberada, evitar sobre-ingeniería).

## Dependencia de versiones anteriores

Depende de v01_core + v02_knowledge (incluidas en esta carpeta). Se
ejecuta de forma independiente.
