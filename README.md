# GENERAL_ENGINEERING_ENGINE

Motor de ingeniería computacional: RESEARCH → UNDERSTAND → MODEL →
DESIGN → SIMULATE → EVALUATE → CRITIQUE → OPTIMIZE → LEARN → ITERATE.

Este repositorio contiene las **9 versiones** del proyecto, organizadas
para que cada una pueda inspeccionarse, ejecutarse y probarse de forma
aislada. **Antes de navegar la estructura, lee `ARCHITECTURE.md`** — explica
por qué esto son 9 fases acumulativas de un mismo sistema, no 9 forks
independientes, y qué implica eso para cómo está organizado el código.

## Estructura

```
GENERAL_ENGINEERING_ENGINE/
├── README.md                  (este archivo)
├── ARCHITECTURE.md             cómo se relacionan las 9 versiones
├── LICENSE
├── requirements.txt
├── .gitignore
│
├── versions/
│   ├── VERSION_MAP.md          qué añade cada versión, en detalle
│   ├── v01_core/                Requirements, Design, Experiment Store,
│   │                            Model/Tool Registry, Orchestrator básico
│   ├── v02_knowledge/           + Knowledge Engine (RAG + provenance)
│   ├── v03_physics/             + Physics/Numerical/Simulation/Validation
│   ├── v04_design/              + Design Engine (exploración acotada)
│   ├── v05_optimization/        + Optimization Engine (Optuna)
│   ├── v06_agents/              + Agent Orchestrator (6 agentes LLM)
│   ├── v07_propulsion_domain/   + Domain Pack formalizado
│   ├── v08_discovery_report/    + Report Generator + Discovery Mode
│   └── v09_advanced_ai/         + interfaces de Scientific ML (sin implementar)
│
├── shared/
│   └── documentation/
│       └── INVENTORY.md        archivo → versión → función → dependencias
│
└── tools/
    ├── run_version.py          corre tests o demo de una versión aislada
    ├── compare_versions.py     diff conceptual entre dos versiones
    └── package_project.py      empaqueta el proyecto completo en .zip
```

## Quickstart

```bash
# Correr los tests de una versión específica, aislada del resto:
python tools/run_version.py v05_optimization

# Correr el script de demo principal de esa versión:
python tools/run_version.py v05_optimization --demo

# Ver qué versiones hay:
python tools/run_version.py --list

# Ver qué cambió entre dos versiones:
python tools/compare_versions.py v04_design v05_optimization
```

Cada `versions/vXX_.../README.md` documenta cómo instalarla y
ejecutarla por su cuenta (con su propio `pyproject.toml`), sin pasar por
`tools/`.

## Validación realizada

Las 9 versiones fueron probadas de forma **aislada** (`PYTHONPATH`
apuntando solo a esa carpeta, sin visibilidad de versiones
posteriores):

| Versión | Tests | Import boundary (`core ↛ domains/agents`) |
|---|---|---|
| v01_core | 34/34 ✅ | 2/2 contratos ✅ |
| v02_knowledge | 50/50 ✅ | 2/2 contratos ✅ |
| v03_physics | 125/125 ✅ | 2/2 contratos ✅ |
| v04_design | 143/143 ✅ | 2/2 contratos ✅ |
| v05_optimization | 155/155 ✅ | 2/2 contratos ✅ |
| v06_agents | 177/177 ✅ | 3/3 contratos ✅ |
| v07_propulsion_domain | 186/186 ✅ | 3/3 contratos ✅ |
| v08_discovery_report | 196/196 ✅ | 3/3 contratos ✅ |
| v09_advanced_ai | 200/200 ✅ | 3/3 contratos ✅ |

v01–v05 verifican 2 contratos (`core`/`infrastructure` no dependen de
`domains`) porque `agents/` todavía no existe en esas fases — no tendría
sentido, ni sería ejecutable, un contrato "no depende de agents" sobre un
paquete inexistente. El tercer contrato (`domains no depende de agents`)
se activa desde v06_agents, que es donde `agents/` aparece por primera
vez. Los 9 números de esta tabla se corrieron de nuevo en esta sesión con
`lint-imports` real, no se copiaron de una versión anterior del README —
antes de esta corrección, `lint-imports` fallaba con `Could not find
package 'agents'` en v01–v05 y no llegaba a evaluar ningún contrato (ver
`P1_P2_IMPLEMENTATION_REPORT.md`).

Ver `shared/documentation/INVENTORY.md` para el detalle archivo por
archivo, y `versions/VERSION_MAP.md` para qué construye cada fase.

## Estado del proyecto

Esto es **V1** del General Engineering Discovery & Simulation Engine —
el primer dominio implementado es propulsión satelital (cold-gas
thruster). El diseño está preparado desde el núcleo para incorporar
otros dominios (estructuras, térmico, semiconductores, etc.) como
Domain Packs nuevos, sin tocar `core/`.

**Limitación conocida en las 9 versiones:** no hay servidor Ollama
disponible en el entorno donde se construyó y validó este proyecto —
`v06_agents` en adelante se probó con un `ModelProvider` de respuestas
guionizadas (`ScriptedModelProvider`), no contra un LLM real. El
`OllamaProvider` está implementado desde v01 pero nunca se ejercitó
contra un servidor Ollama de verdad.
