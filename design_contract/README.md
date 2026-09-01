# design_contract

Design & DesignSpace Engine: transforma un `CandidateDesign` en un
`Design` formal, validado y trazable — independiente de dominio.

Ver `DESIGN_DESIGNSPACE_CONTRACT.md` (raíz del repositorio) para la
documentación completa, y `DESIGN_DESIGNSPACE_IMPLEMENTATION_REPORT.md`
para el informe de esta fase.

## Por qué vive fuera de `versions/`

Mismo razonamiento que `requirement_contract/` (fase anterior, ver su
propio README.md): `versions/v01_core`…`v09_advanced_ai` son el arco
histórico ya auditado y congelado de "V1". Esta fase es trabajo nuevo,
posterior a esa auditoría, y depende de `v09_advanced_ai` (para
`core.validation.dimensional_analysis`, `core.design.schema`,
`core.requirements.schema`) y de `requirement_contract` (para `Value`,
`Provenance`, `Priority`, `Uncertainty`) como librerías, no como copias.

## Instalación (tres pasos)

```bash
pip install -e ../versions/v09_advanced_ai
pip install -e ../requirement_contract
pip install -e ".[dev]"
```

## Cómo ejecutarla

```bash
# bash
export PYTHONPATH="$(pwd):$(pwd)/../requirement_contract:$(pwd)/../versions/v09_advanced_ai"
pytest -q
lint-imports

# PowerShell
$env:PYTHONPATH = "$PWD;$PWD\..\requirement_contract;$PWD\..\versions\v09_advanced_ai"
pytest -q
lint-imports
```

## Qué NO incluye esta fase (deliberado — ver DESIGN_DESIGNSPACE_IMPLEMENTATION_REPORT.md)

- Simulation, Evaluation, Optimization reales (solo interfaces mínimas
  de integración, sin conectar).
- CFD, FEA, CAD completo, nuevos solvers/modelos físicos.
- Integración de `OptimizationAgent` (decisión pendiente de fases anteriores).
- Algoritmos de búsqueda reales más allá de grid/random deterministas
  (`GridSweepDesignGenerator`, `RandomSamplingDesignGenerator`) — Bayesian/
  evolutionary/LLM-guided quedan como `SearchStrategyKind` sin implementar.
- Sistema de embeddings para Novelty (solo distancia paramétrica simple).
- Persistencia (sin `DesignRepository`/store — versionado en memoria).
