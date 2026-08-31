# requirement_contract

Requirement Contract Engine: transforma un `RequirementCandidate` (lo que
un LLM u otra fuente no confiable propone) en un `Requirement` formal,
validado y trazable — sin que el proponente tenga autoridad para saltarse
ninguna validación determinista.

Ver `REQUIREMENT_CONTRACT.md` (raíz del repositorio) para la documentación
completa del contrato, y `REQUIREMENT_IMPLEMENTATION_REPORT.md` para el
informe de esta fase.

## Por qué vive fuera de `versions/`

`versions/v01_core` … `v09_advanced_ai` documentan las 9 fases acumulativas
de "V1" del proyecto, ya auditadas y congeladas (ver `AUDIT_REPORT.md` en
la raíz). Esta fase es trabajo nuevo, posterior a esa auditoría — se trata
como un paquete Python independiente que **depende de `v09_advanced_ai`
como librería** (para reutilizar `core.validation.dimensional_analysis` y
`core.requirements.schema`), no como una copia ni como una décima carpeta
de `versions/`.

## Instalación (dos pasos — monorepo sin publicar a un índice)

```bash
# 1. El paquete del que dependemos (unidades, schemas base) — editable, para
#    que cualquier fix en v09_advanced_ai se refleje sin reinstalar.
pip install -e ../versions/v09_advanced_ai

# 2. Este paquete.
pip install -e ".[dev]"
```

En PowerShell es el mismo comando (`pip install -e ...` funciona igual).

## Cómo ejecutarla

Los tests importan tanto `requirement_contract` (este paquete) como `core`
(de v09_advanced_ai) — con el `pip install -e` de ambos, ambos quedan
resolubles sin tocar `PYTHONPATH` manualmente. Si se prefiere no instalar
y solo apuntar `PYTHONPATH` directamente (consistente con cómo el resto
del repositorio corre sus tests aislados):

```bash
# bash
export PYTHONPATH="$(pwd):$(pwd)/../versions/v09_advanced_ai"
pytest -q
lint-imports

# PowerShell
$env:PYTHONPATH = "$PWD;$PWD\..\versions\v09_advanced_ai"
pytest -q
lint-imports
```

## Qué NO incluye esta fase (deliberado, ver REQUIREMENT_IMPLEMENTATION_REPORT.md)

- Conversation Engine / NL→RequirementCandidate real vía LLM.
- `EngineeringProblem` (el agregador de muchos Requirements) — solo existen
  dos funciones puras de traducción mínima en `requirement_contract/integration.py`
  hacia `core.requirements.schema.Constraint`/`Parameter`, sin conectarlas
  a ningún pipeline vivo.
- Design Engine, Optimization, CFD/FEA/CAD, nuevos modelos físicos.
- Persistencia (no hay un `RequirementStore` — el versionado/locking es
  puramente en memoria, ver `versioning.py`).
