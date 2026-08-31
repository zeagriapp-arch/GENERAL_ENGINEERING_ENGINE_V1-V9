# P1_P2_IMPLEMENTATION_REPORT

**Fecha:** 2026-08-30
**Alcance:** ejecución de Priority 1 (reproducibilidad de `import-linter`) y Priority 2 (auditoría de las 4 tools con handler inexistente en `config/tools.yaml`) de `IMPLEMENTATION_PLAN.md`, bajo las reglas explícitas del usuario: solo corrección/consolidación, nada de funcionalidad nueva, `OptimizationAgent` sin conectar, y cualquier hallazgo arquitectónico grande se reporta antes de tocarlo.

**Resultado en una frase:** ambas prioridades se resolvieron sin escribir una sola línea de código de negocio — P1 fue una corrección real de configuración (5 archivos `pyproject.toml`), P2 resultó ser, tras investigar, un caso ya documentado por el propio proyecto que solo necesitaba consolidarse en la documentación (comentarios + README), no repararse. No apareció ningún problema arquitectónico nuevo que requiera tu decisión — la única decisión pendiente sigue siendo la que ya identificamos y que dejaste explícitamente para después: qué hacer con `OptimizationAgent`.

---

## P1 — Reproducibilidad de `import-linter`

### Qué cambié

En `versions/{v01_core, v02_knowledge, v03_physics, v04_design, v05_optimization}/pyproject.toml`, sección `[tool.importlinter]`:

- `root_packages` pasó de `["core", "agents", "domains", "infrastructure"]` a `["core", "domains", "infrastructure"]`.
- El contrato `"Core no depende de domains ni de agents"` (forbidden=`[domains, agents]`) se renombró a `"Core no depende de domains"` (forbidden=`[domains]`).
- El contrato `"Domains no dependen de agents"` se **eliminó** de estas 5 versiones (no tiene sentido un contrato "no depende de X" sobre un paquete X que no existe todavía).
- El contrato `"Infrastructure no depende de domains ni agents"` se renombró a `"Infrastructure no depende de domains"` (forbidden=`[domains]`).
- Añadí un comentario explicando por qué, para que quien abra el archivo en el futuro entienda que es intencional y no un recorte accidental.

`v06_agents` a `v09_advanced_ai` **no se tocaron** — ya funcionaban correctamente (`agents/` existe desde v06, así que sus 3 contratos siempre fueron válidos).

### Por qué

`root_packages` le dice a `import-linter` qué paquetes debe poder importar para analizar el grafo de dependencias. Listar `"agents"` en v01–v05, donde ese directorio no existe todavía, hacía que el comando fallara **antes de evaluar un solo contrato**:

```
$ cd versions/v01_core && PYTHONPATH=. lint-imports
Could not find package 'agents' in your Python path.
```

Esto es exactamente lo que el README documentaba como "3/3 contratos ✅" para esas 5 versiones — una afirmación que, tal como estaba configurado el proyecto, no se podía reproducir corriendo el comando que el propio README cita.

**Importante:** la regla de arquitectura en sí (`core`/`infrastructure` no dependen de `domains`) siempre se cumplió — lo verifiqué con `grep -rn "^from domains\|^import domains" core/ infrastructure/` en las 5 versiones antes y después del cambio, cero resultados en ambos casos. Lo que estaba roto era la *herramienta de verificación*, no el código de negocio.

### Archivos modificados (P1)

| Archivo | Cambio |
|---|---|
| `versions/v01_core/pyproject.toml` | `[tool.importlinter]`: 3→2 contratos, quitar `agents` de `root_packages` |
| `versions/v02_knowledge/pyproject.toml` | ídem |
| `versions/v03_physics/pyproject.toml` | ídem |
| `versions/v04_design/pyproject.toml` | ídem |
| `versions/v05_optimization/pyproject.toml` | ídem |
| `README.md` (raíz) | tabla de validación: `3/3 contratos` → `2/2 contratos` para v01–v05, + nota explicando por qué, + nota de que los 9 números se re-corrieron en esta sesión |
| `ARCHITECTURE.md` (raíz) | nota aclaratoria en "Regla de arquitectura verificada en las 9 versiones" |

### Resultados — import-linter, ANTES

| Versión | Resultado del comando `lint-imports` documentado en el README |
|---|---|
| v01_core | ❌ `Could not find package 'agents' in your Python path.` (no evalúa contratos) |
| v02_knowledge | ❌ ídem |
| v03_physics | ❌ ídem |
| v04_design | ❌ ídem |
| v05_optimization | ❌ ídem |
| v06_agents | ✅ `Contracts: 3 kept, 0 broken.` |
| v07_propulsion_domain | ✅ `Contracts: 3 kept, 0 broken.` |
| v08_discovery_report | ✅ `Contracts: 3 kept, 0 broken.` |
| v09_advanced_ai | ✅ `Contracts: 3 kept, 0 broken.` |

### Resultados — import-linter, DESPUÉS (corrido en esta sesión, tras el fix)

| Versión | Resultado |
|---|---|
| v01_core | ✅ `Contracts: 2 kept, 0 broken.` (35 files, 24 dependencies) |
| v02_knowledge | ✅ `Contracts: 2 kept, 0 broken.` (42 files, 35 dependencies) |
| v03_physics | ✅ `Contracts: 2 kept, 0 broken.` (71 files, 75 dependencies) |
| v04_design | ✅ `Contracts: 2 kept, 0 broken.` (74 files, 86 dependencies) |
| v05_optimization | ✅ `Contracts: 2 kept, 0 broken.` (78 files, 102 dependencies) |
| v06_agents | ✅ `Contracts: 3 kept, 0 broken.` (88 files, 145 dependencies) — sin cambios |
| v07_propulsion_domain | ✅ `Contracts: 3 kept, 0 broken.` (90 files, 147 dependencies) — sin cambios |
| v08_discovery_report | ✅ `Contracts: 3 kept, 0 broken.` (92 files, 158 dependencies) — sin cambios |
| v09_advanced_ai | ✅ `Contracts: 3 kept, 0 broken.` (94 files, 159 dependencies) — sin cambios |

**Las 9 versiones ahora ejecutan `lint-imports` con éxito, de forma aislada, exactamente como documenta el README.**

### Tests — ANTES vs. DESPUÉS (verificación de que no se introdujo ningún cambio de comportamiento)

| Versión | Antes | Después | ¿Cambió algo? |
|---|---|---|---|
| v01_core | 34 passed | 34 passed | No |
| v02_knowledge | 50 passed | 50 passed | No |
| v03_physics | 125 passed | 125 passed | No |
| v04_design | 143 passed | 143 passed | No |
| v05_optimization | 155 passed | 155 passed | No |
| v06_agents | 177 passed | 177 passed | No |
| v07_propulsion_domain | 186 passed | 186 passed | No |
| v08_discovery_report | 196 passed | 196 passed | No |
| v09_advanced_ai | 200 passed | 200 passed | No |

Total: **1.266 tests, antes y después, cero regresiones.** El cambio fue puramente en metadata de linting (`pyproject.toml`), nunca importada por ningún módulo de negocio — no había manera de que afectara a pytest, y así se confirmó.

### El "comando correcto" no cambió — por eso no toqué las instrucciones de instalación

Siguiendo tu instrucción de actualizar documentación solo si el comando cambia: `lint-imports` (sin argumentos, con `PYTHONPATH` apuntando a la carpeta de la versión) sigue siendo exactamente el comando correcto en las 9 versiones — no cambié ninguna instrucción de "Cómo ejecutarla" en los README de cada versión. Lo único que actualicé es el **resultado documentado** de correr ese comando (la tabla de contratos en el README raíz), porque ese número sí cambió (3→2 para v01–v05) como consecuencia directa de la corrección.

---

## P2 — Las 4 tools con handler inexistente

### Investigación (antes de decidir nada)

Antes de tocar `config/tools.yaml`, verifiqué:

1. **¿Desde cuándo existen estas 4 entradas?** `diff` byte a byte de `config/tools.yaml` entre las 9 versiones → **es idéntico en las 9**, nunca fue modificado desde v01_core. Esto descarta que sean "restos de un refactor posterior" — están ahí desde el primer commit conceptual del proyecto.

2. **¿El propio proyecto ya sabía esto?** Sí. `versions/v01_core/README.md`, sección "Limitaciones conocidas" (texto original, sin tocar por mí):

   > `config/tools.yaml` y `config/models.yaml` ya anticipan handlers de fases futuras (`search_knowledge`, `run_simulation`, `run_optimizer`, etc.) que aún no existen como módulos — invocarlos devuelve un error explícito manejado (`ToolResult(ok=False, ...)`), no un crash. Es diseño intencional (forward declaration), no un bug.

   Es decir: la existencia de handlers no resueltos en `tools.yaml` **no es un descubrimiento de esta auditoría** — es un patrón de diseño que el propio v01 documentó y justificó desde el principio (declarar el contrato completo del Tool Registry por adelantado, confiando en que `ToolRegistry.invoke()` falla de forma segura si el handler todavía no existe).

3. **¿Sigue siendo intencional o quedó huérfano?** Revisé el documento de diseño original (`versions/v09_advanced_ai/ARCHITECTURE.md`, sección 14 "Tool System"), que **es el borrador original de `config/tools.yaml`** — literalmente contiene `handler: core.evaluation.engine:compare` y `handler: core.optimization.optuna_backend:suggest` como parte del ejemplo de diseño, junto a interfaces planeadas `core/evaluation/interfaces.py: Evaluator.compare(...)`, `core/optimization/interfaces.py: Optimizer.suggest(search_space, history)`, `core/critic/interfaces.py: Critic.review(...)`.

4. **¿Qué pasó realmente durante la implementación (v01→v09)?** La funcionalidad *sí* se construyó, pero tomó una forma distinta a la del boceto original — una evolución de diseño real, no un olvido:
   - "Evaluator.compare()" → terminó como `core/design/candidate.py:evaluate_requirements()` (compartida entre Design Engine y Optimizer, decisión explícita anti-duplicación de v05) + `agents/analysis_agent.py:compute_evaluation()`. Firma distinta, ubicación distinta (`core/design/` y `agents/`, no `core/evaluation/`).
   - "Critic.review()" → terminó como `agents/critic_agent.py:CriticAgent.critique()`, con la mejora deliberada de que el veredicto se calcula ANTES de invocar al LLM (más estricta que el boceto original).
   - "Optimizer.suggest(search_space, history) -> punto único" (API ask/tell) → terminó como `OptunaOptimizer.optimize(requirements, design_space, budget, seed) -> OptimizationResult` (corre el estudio completo internamente vía `optuna.Trial`). Es una decisión de API distinta, no un `suggest()` sin terminar.
   - "Uncertainty Engine" (`core/uncertainty/engine.py: sensitivity_analysis`, `propagate`) → nunca se construyó. Solo existe `core/uncertainty/sensitivity.py:SensitivityAnalyzer` (interfaz abstracta, sin implementación, en una ruta de módulo distinta a la que cita `tools.yaml`) — explícitamente Phase 9, diferido a propósito.

5. **¿Algo invoca hoy estas 4 tools?** No. `grep -rn "run_optimizer\|evaluate_design\|run_sensitivity_analysis\|run_uncertainty_analysis" versions/*/agents/` no encuentra ningún `invoke_tool(...)` real — solo la mención en el docstring de `OptimizationAgent`, que dice explícitamente **"Este agente NUNCA invoca `run_optimizer` directamente"**. Es decir, ni siquiera el agente más relacionado con esa tool la usa. Confirmado también que `core/optimization/` no existe en absoluto en v01–v04 (se añade en v05), así que `run_optimizer` fue inválido por partida doble en esas versiones.

6. **¿v09 (la versión final) seguía documentando esto?** Solo a medias. La sección "Limitaciones conocidas — resumen de todo el proyecto V1" de `versions/v09_advanced_ai/README.md` sí carga hacia adelante la limitación de `OptimizationAgent` no conectado (heredada de v06) y las interfaces de Phase 9 sin implementar, pero **no** repitió la advertencia específica sobre `tools.yaml` que sí estaba en v01. Este es el único vacío real que encontré.

### Decisión tomada

Ninguna de las 4 opciones (A/B/C/D) tal como estaban planteadas encaja perfectamente, así que la decisión es una combinación justificada por lo anterior:

- **No es (A):** implementarlas ahora violaría la instrucción explícita de "nada de funcionalidad nueva" — y además no hay un caso de uso real esperándolas (nada las invoca).
- **Es (B), con matiz:** no son "restos de una versión anterior" en el sentido de código que se dejó de mantener — son **forward declarations deliberadas desde v01**, documentadas como tales desde el primer día, que nunca llegaron a resolverse porque el proyecto evolucionó por un camino de diseño distinto (y, para las de Phase 9, porque se decidió explícitamente no construir esa fase todavía).
- **No es (C):** no hay un módulo real al que "reapuntar" sin inventar algo nuevo. `evaluate_requirements()`/`compute_evaluation()` tienen firmas y ubicaciones arquitectónicas distintas (viven en `core/design/` y `agents/`, no en un `core/evaluation/` neutral) — remapear `tools.yaml` a esas funciones sería más una operación de diseño nueva que una corrección de configuración, y tocaría la pregunta pendiente de `OptimizationAgent` que dejaste explícitamente para después.
- **No es (D) en el sentido de "borrar":** borrar las 4 entradas eliminaría una señal de diseño intencional que el proyecto ya había documentado, sin ganar nada — hoy no rompen nada (`ToolRegistry.invoke()` falla de forma segura y controlada) y nadie las invoca.

**Acción tomada: documentar de forma exhaustiva, en el propio archivo de configuración y en el README de v09, por qué existen y por qué siguen ahí sin resolver — sin tocar ni una línea de código.** Esto es consolidación, no reparación: el "defecto" real no era la existencia de las 4 líneas, sino que su justificación estaba enterrada en el README de v01 y no era visible desde donde más importa (el propio `tools.yaml`, y el resumen final en v09).

### Archivos modificados (P2)

| Archivo | Cambio |
|---|---|
| `versions/v09_advanced_ai/config/tools.yaml` | Añadido bloque de comentarios explicando el origen y estado de las 4 tools (`evaluate_design`, `run_optimizer`, `run_sensitivity_analysis`, `run_uncertainty_analysis`). **Cero cambios funcionales** — mismos `handler`, `description`, `allowed_agents` que antes. |
| `versions/v09_advanced_ai/README.md` | Una viñeta nueva en "Limitaciones conocidas", recuperando la advertencia de v01 que se había dejado de repetir. |

**v01–v08 no se tocaron.** v01 ya se auto-documentaba correctamente; v02–v08 heredan el mismo `tools.yaml` sin ningún README que haga la afirmación "3/3 fully wired" que contradiga esto, así que no había nada que corregir ahí — evité tocar 8 archivos adicionales sin necesidad.

### Verificación de que el cambio es puramente documental

```
$ python -c "from config.settings import get_settings; s = get_settings(); print(len(s.tools.tools), 'tools loaded OK')"
16 tools loaded OK

$ pytest -q            # v09_advanced_ai
200 passed in 7.93s    # idéntico a antes del cambio

$ lint-imports          # v09_advanced_ai
Contracts: 3 kept, 0 broken.   # idéntico a antes del cambio
```

Los comentarios YAML no afectan al parseo (`yaml.safe_load` los descarta) ni a la validación Pydantic (`ToolsConfig`) — confirmado cargando la configuración real, no solo asumido.

### Sobre `OptimizationAgent`

Tal como pediste explícitamente: **no lo conecté al Orchestrator ni a `discovery.py`.** Sigue exactamente como estaba: implementado en `agents/optimization_agent.py`, testeado en aislamiento (`tests/unit/agents/test_optimization_agent.py`), y sin instanciar en `agents/orchestrator.py`. El comentario nuevo en `tools.yaml` junto a `run_optimizer` señala este estado pero no lo modifica. Queda pendiente la conversación de arquitectura que propusiste para decidir cómo (o si) integrarlo — ver Priority 3 de `IMPLEMENTATION_PLAN.md` para las dos opciones que ya había esbozado (cablearlo con una API de "foco" nueva, o formalizar que queda standalone).

---

## Validación final (checklist solicitado)

1. **Tests V1–V9:** ✅ 1.266 tests totales, todos pasan, en las 9 versiones, antes y después — sin diferencias (tabla arriba).
2. **Import-linter en las 9 versiones:** ✅ las 9 ahora corren y pasan (2/2 en v01–v05, 3/3 en v06–v09) — antes, 5 de 9 fallaban en ejecutar el comando.
3. **Demos end-to-end:** ✅ re-corridos `run_first_experiment.py`, `run_phase6_vertical_slice.py`, `run_phase7_8_vertical_slice.py` (v09) y `run_phase4_vertical_slice.py` (v04, vía `tools/run_version.py --demo`) tras los cambios — resultados numéricos idénticos a la corrida de la auditoría original (mismo seed, mismo determinismo: `thrust=0.8644164761965736`, `Isp=76.82536852473885`, etc.), confirmando cero cambio de comportamiento.
4. **Verificación de imports:** ✅ `grep` manual de `core`/`infrastructure` importando `domains`/`agents` en las 5 versiones afectadas — cero resultados, antes y después.
5. **Verificación de configuración:** ✅ `tomllib.load()` sobre los 5 `pyproject.toml` editados confirma TOML válido y el contrato/root_packages esperado; `get_settings()` sobre v09 confirma que `tools.yaml` sigue cargando sus 16 tools sin error.
6. **Git diff:** el repositorio no tenía control de versiones — inicialicé uno (`git init` + commit baseline) al empezar esta tarea, específicamente para poder darte este diff real. `git diff --stat` contra el baseline pre-P1/P2:
   ```
    ARCHITECTURE.md                            | 12 ++++++++
    README.md                                  | 21 ++++++++++---
    versions/v01_core/pyproject.toml           | 24 ++++++++-------
    versions/v02_knowledge/pyproject.toml      | 24 ++++++++-------
    versions/v03_physics/pyproject.toml        | 24 ++++++++-------
    versions/v04_design/pyproject.toml         | 24 ++++++++-------
    versions/v05_optimization/pyproject.toml   | 24 ++++++++-------
    versions/v09_advanced_ai/README.md         |  5 +++
    versions/v09_advanced_ai/config/tools.yaml | 49 ++++++++++++++++++++++++++++++
    9 files changed, 147 insertions(+), 60 deletions(-)
   ```
7. **Archivos modificados innecesariamente:** ninguno. `git status --short` mostró exactamente estos 9 archivos (8 de contenido + este informe se añade después) — coincide exactamente con lo planeado, nada se tocó "de paso". Los artefactos generados por correr tests/lint (`*.db`, `.import_linter_cache/`, `.pytest_cache/`, `__pycache__/`) se generaron y se eliminaron en cada ronda de verificación, ya cubiertos por `.gitignore`.

---

## Problemas restantes (ninguno nuevo, ninguno bloqueante)

No apareció ningún problema arquitectónico nuevo durante P1/P2 que requiriera detenerme a preguntarte — todo lo que toqué era exactamente lo que `AUDIT_REPORT.md` ya había identificado, y la investigación de P2 confirmó la causa sin sorpresas que cambien la arquitectura.

Lo que queda abierto, todo ya conocido y explícitamente fuera de esta ronda:

- **`OptimizationAgent`** — decisión pendiente, como acordamos, para la próxima conversación de arquitectura (Priority 3 de `IMPLEMENTATION_PLAN.md`).
- **`core/critic/` y `core/evaluation/`** — paquetes vacíos (Priority 4). No los toqué en esta ronda porque tu pedido se limitó explícitamente a P1 y P2.
- **H-5/H-6 del audit** (confidence heurística sin marcar, mojibake de consola en Windows) — cosméticos, Priority 5, sin tocar.
- **H-7** (NL→Requirements) — confirmado que sigue sin existir en ninguna versión; no se toca, es la conversación de la "siguiente etapa" que mencionas al final de tu mensaje.

**Estado de la base tras P1+P2: limpia y reproducible según el criterio que pediste** — cualquiera que clone el repo, instale las dependencias, y corra `pytest -q` + `lint-imports` en cualquiera de las 9 carpetas obtiene exactamente los números que la documentación afirma, sin excepciones ni pasos ocultos.
