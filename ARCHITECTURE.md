# ARCHITECTURE.md — Cómo se relacionan las 9 versiones

## Lo primero que hay que entender: esto NO son 9 forks independientes

Cuando se pidió esta reorganización, la plantilla sugerida asumía un
escenario común: un asistente que reescribe el proyecto desde cero cada
vez que se le pide una "versión nueva", generando 9 copias parcialmente
redundantes del mismo código. **Ese no es el caso aquí.**

Este proyecto se construyó como **una sola base de código evolucionando
por fases**, donde cada fase (v01→v09) añade módulos nuevos sobre los ya
existentes — como si fuera un único repositorio con 9 tags de Git
consecutivos, no 9 ramas paralelas. La prueba está en el inventario
(`shared/documentation/INVENTORY.md`): de 159 archivos totales, solo 5
fueron modificados alguna vez después de su creación; los 154 restantes
se escribieron una vez y nunca se volvieron a tocar.

## Qué significa esto para la estructura de carpetas

Cada carpeta `versions/vXX_.../` es un **snapshot completo y funcional**
del proyecto tal como existía al cierre de esa fase — no un diff, no una
carpeta con solo los archivos "nuevos". Esto es deliberado:

1. **Cada versión debe poder ejecutarse de forma independiente**
   (regla explícita de esta tarea). Con una arquitectura acumulativa, la
   única forma de garantizar eso sin reescribir imports es que cada
   carpeta contenga el árbol completo tal como era en ese momento.
2. **Cada versión fue validada de forma aislada** — no es una promesa,
   se verificó: los tests de cada `vXX/` corren con `PYTHONPATH=vXX/`
   apuntando SOLO a esa carpeta, sin visibilidad de las carpetas de
   versiones posteriores. Los conteos de tests (34, 50, 125, 143, 155,
   177, 186, 196, 200) son exactamente los que existían al cerrar cada
   fase — no números inflados retroactivamente.

## Por qué `shared/` casi no tiene código

La plantilla original sugería mover "componentes compartidos entre
varias versiones" a `shared/`. El problema: en una arquitectura
acumulativa, prácticamente TODO el `core/` de v09 es "compartido" con
v04 en el sentido de que v04 tiene una versión temprana del mismo
archivo — pero no son copias idénticas congeladas, son el mismo archivo
en distintos puntos de su evolución (5 de ellos fueron literalmente
editados entre versiones, ver inventario).

Extraer un `shared/core/` real habría exigido reescribir las
importaciones de las 9 versiones para apuntar a una ubicación externa
común — con alto riesgo de romper algo, que es exactamente lo que las
reglas de esta tarea prohíben ("NO cambies la lógica", "NO rompas
referencias"). Se optó por la alternativa más segura: cada versión es
autocontenida, y `shared/` guarda solo documentación transversal
(este archivo, el inventario, el mapa de versiones).

## Mapa de dependencias conceptuales entre fases

```
v01_core           — Requirements, Design, Experiment Store, Model/Tool
                      Registry, Orchestrator síncrono (steps stub)
   │
   ▼ (+ Knowledge Engine)
v02_knowledge       — RAG híbrido, provenance, conocimiento curado del
                      cold-gas thruster (6 fuentes públicas NASA/Wikipedia)
   │
   ▼ (+ Physics/Numerical/Simulation/Validation Engines)
v03_physics         — PhysicsModel del cold-gas thruster, modelos
                      genéricos de benchmark, ODE solver, V&V
   │
   ▼ (+ Design Space/Generator/Engine)
v04_design          — exploración acotada de diseños (grid sweep,
                      random sampling) validada contra física real
   │
   ▼ (+ Optimizer)
v05_optimization    — búsqueda matemática real (Optuna, TPE), Pareto
                      front multi-objetivo
   │
   ▼ (+ Agentes LLM)
v06_agents          — Research/Design/Simulation/Analysis/Critic/
                      Optimization Agents; el LLM propone, nunca decide
   │
   ▼ (+ Domain Pack formal)
v07_propulsion_domain — Requirements builder específico del dominio,
                        métricas de evaluación propias
   │
   ▼ (+ Report Generator + Discovery Mode)
v08_discovery_report — responde las 12 preguntas de "Definition of Done"
                       sin LLM; conecta Design Space+Optimizer+Store+Report
   │
   ▼ (+ interfaces ML, sin implementar)
v09_advanced_ai     — SurrogateModel/ActiveLearningStrategy (stubs),
                      preparación explícita para Phase 9+ real
```

## Regla de arquitectura verificada en las 9 versiones

`core/` nunca importa `domains/` ni `agents/`. `domains/` nunca importa
`agents/`. Esto se verificó con `import-linter` corriendo de forma
independiente en cada una de las 9 carpetas — no solo en el estado
final. Ver `tools/compare_versions.py` para reproducirlo.

## Documento de arquitectura técnica original

El diseño técnico completo (interfaces, schemas, decisiones de stack,
riesgos) está en `versions/v09_advanced_ai/ARCHITECTURE.md` — es el
documento de diseño original del proyecto, se conserva sin modificar
dentro de la versión final.
