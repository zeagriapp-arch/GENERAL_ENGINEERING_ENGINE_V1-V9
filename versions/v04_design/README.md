# v04_design

## Qué contiene

Todo lo de v03_physics, más el **Design Engine**:
- `DesignSpace`/`DesignVariable`: se construye automáticamente desde `Requirements` — variables `FREE` con `range` se vuelven explorables con bounds explícitos.
- `DesignGenerator`: interfaz única con dos implementaciones intercambiables — `RandomSamplingGenerator` (Monte Carlo) y `GridSweepGenerator` (determinista).
- `DesignEngine.explore()`: genera candidato → simula con física real (v03) → valida constraints duros/blandos → PASS/FAIL con razones explícitas.
- `Design` extendido con `operating_conditions`, `manufacturing_constraints`, `provenance`.

## Capacidades

Puede explorar un espacio de diseño acotado y devolver solo
configuraciones físicamente válidas que cumplen los requisitos — sin
optimización matemática todavía (eso es v05) y sin LLM (eso es v06).

## Qué cambió respecto a v03_physics

- **Nuevo**: `core/design/{design_space,generator,engine}.py`.
- **Modificado**: `core/design/schema.py` — `Design` gana 3 campos nuevos (ver arriba). Los campos son `Field(default_factory=...)`, así que no rompe ningún `Design` creado por código de v01-v03.

## Cómo ejecutarla

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                    # 143 tests
python scripts/run_phase4_vertical_slice.py  # grid sweep vs random sampling, mismo resultado físico
```

## Dependencias

Mismas que v03_physics — sin dependencias nuevas.

## Tests disponibles

143 tests (125 heredados + 18 nuevos de Design Engine).

## Limitaciones conocidas

- Bug real encontrado y corregido durante el desarrollo de esta versión
  (documentado en el código): un candidato podía "desaparecer" del
  conteo si el budget se agotaba a mitad de su evaluación. Ya
  corregido en esta versión — un candidato, una vez comprometido contra
  el budget, siempre se completa.
- `DesignEngine._build_design`/`_check_design_space_constraints`/
  `_evaluate_requirements` son métodos privados en ESTA versión — en
  v05 se extraen a un módulo compartido (`core/design/candidate.py`)
  para reutilizarlos también en el Optimizer. Ver `core/design/engine.py`
  de v05 para comparar.

## Dependencia de versiones anteriores

Depende de v01-v03 (incluidas en esta carpeta). Se ejecuta de forma
independiente.
