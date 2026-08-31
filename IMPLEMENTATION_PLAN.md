# IMPLEMENTATION_PLAN — GENERAL_ENGINEERING_ENGINE (V1–V9)

Deriva directamente de `AUDIT_REPORT.md`. Todos los ítems son correcciones puntuales y de bajo riesgo — **ninguno** requiere reescribir arquitectura ni tocar la física/matemática ya validada. Nada de esto se ha implementado todavía; esto es la propuesta para aprobación, tal como pide el prompt de auditoría (paso 10, antes del paso 11).

No se incluye nada de Phase 9 (Scientific ML, uncertainty quantification real, NL→Requirements) — son capacidades futuras deliberadamente fuera de alcance de esta ronda de correcciones, per la regla explícita de la auditoría de no adelantar fases.

---

## Priority 1 — Corregir la verificación de arquitectura para que sea reproducible (H-1)

**Archivos:** `versions/v01_core/pyproject.toml`, `v02_knowledge/pyproject.toml`, `v03_physics/pyproject.toml`, `v04_design/pyproject.toml`, `v05_optimization/pyproject.toml` (sección `[tool.importlinter]` en cada uno).

**Qué cambiar:** en esas 5 versiones, `root_packages` lista `["core", "agents", "domains", "infrastructure"]` pero `agents/` no existe todavía en esas fases. Cambiar a `root_packages = ["core", "domains", "infrastructure"]` y quitar `"agents"` de `forbidden_modules` en los contratos de esas 5 versiones (ya que no hay nada que prohibir si el módulo no existe).

**Por qué:** hoy `lint-imports` no puede ejecutarse en absoluto sobre v01–v05 (falla con `Could not find package 'agents'`), lo cual contradice la tabla de validación del README línea por línea para 5 de 9 filas. La regla real (`core` no depende de nada de dominio/agente) ya se cumple — esto es arreglar la *herramienta de verificación*, no el código de negocio.

**Dependencias:** ninguna. Cambio aislado en metadata de linting.

**Cómo probarlo:**
```bash
cd versions/v01_core && PYTHONPATH=. lint-imports   # debe imprimir "3 kept, 0 broken" (o el número de contratos que queden tras quitar la referencia a agents)
```
Repetir para v02–v05. Además, volver a correr el suite de tests completo de cada una para confirmar que no se rompió nada (`pytest -q` desde cada carpeta, con `PYTHONPATH` acotado) — deben seguir dando 34/50/125/143/155.

**Riesgo:** ninguno — es un archivo de configuración de una herramienta de lint, no importado por ningún módulo de negocio.

---

## Priority 2 — Eliminar la inconsistencia entre `config/tools.yaml` y los handlers reales (H-4)

**Archivo:** `versions/v09_advanced_ai/config/tools.yaml` (y las versiones donde se introdujo cada entrada: `run_optimizer`/`evaluate_design` desde v05/v01 respectivamente si aplica, `run_sensitivity_analysis`/`run_uncertainty_analysis` desde donde se hayan declarado — confirmar con `grep -rn "run_optimizer\|evaluate_design\|run_sensitivity_analysis\|run_uncertainty_analysis" versions/*/config/tools.yaml` antes de tocar nada, para editar todas las versiones afectadas de forma consistente, no solo v09).

**Opción A (recomendada, mínimo esfuerzo, corrige el gap real):** implementar los handlers que son plausibles ya con lo que existe:
- `core/optimization/optuna_backend.py:suggest(...)` — función libre que, dado un `DesignSpace` y el historial de trials, devuelva el siguiente punto sugerido sin correr un `study.optimize()` completo. Esto es lo que necesitaría `OptimizationAgent` si se cablea (ver Priority 3).
- Dejar `evaluate_design`, `run_sensitivity_analysis`, `run_uncertainty_analysis` para la Opción B (son genuinamente Phase 9/futuro).

**Opción B (mínimo riesgo, para lo que es explícitamente Phase 9):** comentar esas 3 entradas en `tools.yaml` con una nota `# Habilitar en Phase 9 cuando exista core/uncertainty/engine.py y core/evaluation/engine.py`, en vez de dejarlas declaradas como si ya existieran.

**Por qué:** hoy un agente que invoque cualquiera de estas 4 tools recibe un fallo silencioso (`ToolResult(ok=False)`) en vez de un error de configuración detectado en CI. Es inofensivo mientras nada las invoque (confirmado que hoy nada las invoca), pero es exactamente el tipo de "deuda invisible" que explota en cuanto alguien conecta una pieza nueva (ej. Priority 3).

**Cómo probarlo:** un test de "config sanity" nuevo y barato de mantener:
```python
# tests/unit/test_tools_config_handlers_exist.py
import importlib
from config.settings import get_settings

def test_every_declared_tool_handler_is_importable():
    settings = get_settings()
    errors = []
    for name, spec in settings.tools.tools.items():
        module_path, func_name = spec.handler.split(":")
        try:
            mod = importlib.import_module(module_path)
            assert hasattr(mod, func_name), f"{spec.handler}: falta atributo '{func_name}'"
        except ImportError as exc:
            errors.append(f"{name} -> {spec.handler}: {exc}")
    assert not errors, "\n".join(errors)
```
Este test es valioso más allá de esta corrección puntual: previene que la inconsistencia vuelva a aparecer en el futuro. Recomiendo añadirlo permanentemente al suite de v09 (y hacia atrás en las versiones donde aplique) independientemente de qué Opción se elija arriba.

**Riesgo:** bajo. Opción B es notación pura. Opción A añade una función nueva sin tocar `OptunaOptimizer.optimize()` existente (que sigue siendo el único camino real de optimización).

---

## Priority 3 — Decidir el destino de `OptimizationAgent` (H-3)

**Archivos:** `agents/orchestrator.py`, `core/orchestrator/discovery.py`.

**Opción A — Cablearlo:** en `run_discovery_mode` (o en una nueva variante `run_discovery_mode_with_agent_focus`), antes de cada tanda de `optimizer.optimize()`, invocar `OptimizationAgent.suggest_focus(design_space, result.all_evaluations[-N:])` y usar `variables_to_explore` para, por ejemplo, fijar temporalmente las demás variables o pesar el sampler de Optuna. Requiere decidir una API concreta de "foco" que `OptunaOptimizer` pueda consumir — hoy no existe ese contrato, habría que diseñarlo (no es un cambio de una línea).

**Opción B — Documentarlo como standalone (mínimo esfuerzo):** actualizar el README y `ARCHITECTURE.md` para decir explícitamente "6 agentes implementados y testeados; 5 conectados al `AsyncOrchestrator` real, `OptimizationAgent` queda como componente independiente listo para integrarse cuando el Optimizer soporte recibir foco externo" — en vez de listar "6 agentes" sin matiz.

**Recomendación:** Opción B ahora, Opción A cuando haya un caso de uso real que lo necesite (evitar sobre-ingeniería, consistente con la decisión ya tomada para v09/ML). Diseñar la API de "foco" sin un caso de uso concreto es el tipo de trabajo especulativo que el prompt de auditoría pide evitar.

**Cómo probarlo:** si se elige B, no hay código que probar — solo verificar que el README ya no afirma integración que no existe. Si se elige A, el criterio de aceptación es: un test de integración nuevo que corra `run_discovery_mode` dos veces con el mismo seed, una con foco del agente y una sin él, y verifique que el foco efectivamente cambia qué variables explora Optuna (no solo que el código no crashea).

**Riesgo:** Opción A tiene riesgo MEDIO si se hace apresuradamente (tocar `OptunaOptimizer`, componente ya validado con 155+ tests). Opción B tiene riesgo cero.

---

## Priority 4 — Limpieza de paquetes vacíos (H-2)

**Archivos:** `core/critic/__init__.py`, `core/evaluation/__init__.py` en todas las versiones donde existan vacíos (desde v01 en adelante, confirmar con `find versions -path "*/core/critic/__init__.py" -o -path "*/core/evaluation/__init__.py"`).

**Qué hacer:** confirmar con `grep -rn "core\.critic\|core\.evaluation" versions/*/` que, en efecto, nada los importa (ya verificado para v09 en esta auditoría; repetir para v01–v08 antes de tocar nada, dado que cada versión es un snapshot independiente). Si se confirma en las 9, dos alternativas:
- (a) Eliminar los directorios.
- (b) Dejarlos pero con un docstring de una línea en el `__init__.py`: `"""Vacío deliberadamente — la lógica de evaluación/crítica vive en core/design/candidate.py y agents/critic_agent.py."""`.

**Recomendación:** (b) es más seguro dado que estas carpetas existen en las 9 versiones y tocar 9 snapshots históricos para borrar algo tiene más superficie de error que añadir una línea de documentación en cada una.

**Riesgo:** ninguno si se opta por (b). Bajo si se opta por (a) — un `rmdir` no debería romper nada ya que no hay imports, pero conviene re-correr el suite completo de cada versión afectada tras el cambio, no solo confiar en el grep.

---

## Priority 5 — Cosméticos de bajo riesgo

1. **H-6 (encoding Windows):** añadir a cada `scripts/run_*.py`:
   ```python
   import sys
   if sys.platform == "win32":
       sys.stdout.reconfigure(encoding="utf-8")
   ```
   Probar con `python -m scripts.run_phase7_8_vertical_slice` en PowerShell/cmd y confirmar que las tildes se ven bien.

2. **H-5 (confidence heurística):** añadir un comentario explícito donde se asigna (`cold_gas_solver.py`, `simulation/schema.py`) del tipo `# NOTA: heurística binaria (0.9/0.3), no una cuantificación estadística real — ver core/uncertainty/sensitivity.py para el plan de Phase 9`. No renombrar el campo `confidence` todavía (eso sí sería un cambio de schema que rompe compatibilidad con `Results` en 9 versiones — fuera de alcance de una corrección de bajo riesgo).

3. **`.audit_venv/` creado durante esta auditoría:** añadir `.audit_venv/` (o el nombre que se use) a `.gitignore`, o borrarlo si no se quiere conservar el entorno de verificación.

**Riesgo:** cero en los tres casos.

---

## Orden de ejecución recomendado

1. Priority 1 (arreglar tooling de verificación) — habilita que el resto de cambios se pueda verificar correctamente con `lint-imports` real.
2. Priority 2, Opción B primero (comentar las 3 tools genuinamente-futuras) — quita el riesgo inmediato con cero esfuerzo; Opción A (`optuna_backend.py:suggest`) solo si se decide avanzar con Priority 3-A.
3. Priority 4 (limpieza de paquetes vacíos) — independiente de todo lo demás, se puede hacer en paralelo.
4. Priority 5 (cosméticos) — en cualquier momento, no bloquea nada.
5. Priority 3 — requiere una decisión explícita del usuario (Opción A vs. B) antes de tocar código; no ejecutar sin esa decisión.

## Qué NO hacer en esta ronda

- No implementar `core/ml/surrogate.py` ni `core/uncertainty/sensitivity.py` — son Phase 9 por diseño explícito del proyecto.
- No construir NL→Requirements (H-7) — es la capacidad más grande de las pendientes y merece su propia sesión de diseño, no un parche dentro de esta corrección.
- No tocar la física del cold-gas thruster, `OptunaOptimizer.optimize()`, `ExperimentStore`, ni ningún componente listado como WORKING sin hallazgos — están validados y no deben modificarse "por prolijidad".
