# ARCHITECTURE DESIGN DOCUMENT
## General Engineering Discovery & Simulation Engine (GEDE)

**Estado:** Propuesta para revisión — ningún código de implementación incluido.
**Alcance de este documento:** Responder a la Tarea #45 de la especificación: arquitectura concreta, contradicciones a resolver, repository structure, interfaces, schemas, stack, integración con Ollama, tool calling, almacenamiento de experimentos, vertical slice V1, tests, y qué queda preparado para C++/CUDA.

---

## 0. Resumen ejecutivo

GEDE es un motor de investigación de ingeniería computacional. No es un chatbot ni un generador de diseños "mágico": es un pipeline determinista de **research → model → simulate → evaluate → critique → optimize → learn → iterate**, donde el LLM propone hipótesis y las herramientas matemáticas/físicas deciden si son válidas.

Principio rector que condiciona toda decisión de arquitectura de aquí en adelante:

> **El LLM nunca es la fuente de verdad. Es un generador de hipótesis dentro de un sistema que las verifica.**

Esto tiene una consecuencia arquitectónica directa: **CORE debe poder ejecutarse y dar resultados válidos sin ningún LLM presente** (con datos/diseños suministrados programáticamente). Los agentes LLM son un *cliente* de CORE, no una parte de él. Esta separación es la prueba de fuego de que el diseño es correcto.

---

## 1. Contradicciones y decisiones pendientes en la especificación

Antes de fijar la arquitectura, esto es lo que la spec deja ambiguo o parcialmente contradictorio. Necesito tu decisión (o propongo un default razonable, marcado con →).

| # | Tema | Tensión | Propuesta por defecto |
|---|------|---------|------------------------|
| 1 | **SQLite vs PostgreSQL** | Sección 38 dice "dependiendo de complejidad" sin criterio. | → SQLite para V1 (cero fricción de setup), con capa de acceso a datos (Repository pattern) que hace el salto a Postgres un cambio de connection string, no de código. |
| 2 | **Vector store** | Nunca se especifica motor (Chroma, Qdrant, pgvector, FAISS...). | → Chroma embebido para V1 (local, sin servidor extra), detrás de una interfaz `VectorStore` para poder migrar a Qdrant/pgvector cuando haya multiusuario. |
| 3 | **Orquestación de agentes** | Se pide "Orchestrator" pero no si usar un framework (LangGraph, AutoGen, custom) o construirlo a mano. | → Orchestrator **custom** y explícito (máquina de estados simple) en V1. Un framework externo esconde el control de flujo justo donde más necesitas trazabilidad y control de bucles infinitos (sección 35). Se reevalúa en Phase 6. |
| 4 | **Qwen3 vía Ollama para tool calling estructurado** | Tool calling confiable (JSON schema estricto) depende de qué tan bien el modelo respeta grammars/function calling. Ollama lo soporta pero con matices por modelo. | → Usar **structured output vía grammar-constrained decoding** (Ollama soporta `format: json_schema` desde versiones recientes) en vez de confiar en que el modelo "decida" llamar una tool en texto libre. Si el modelo/versión de Ollama no lo soporta bien, fallback a parsing + reintentos con validación Pydantic. |
| 5 | **Definición de "Discovery Mode" vs "Optimization Mode"** | Se describen como dos modos, pero comparten casi todo el pipeline salvo el punto de entrada (Design existente vs. Requirements). | → Modelarlos como el mismo `Orchestrator` con distinto **entry point**, no como dos sistemas separados. Optimization Mode = Discovery Mode con `baseline_design` ya fijado y `architecture_search=False`. |
| 6 | **Nivel de "conocimiento estructurado" en V1** | Sección 8 pide una capa estructurada rica (Component, Property, Equation, Relationship...) pero sección 42 dice no construir "una knowledge graph gigantesca" en V1. | → V1 implementa el **schema** completo (para no tener que migrar datos después) pero la **población** es manual/curada para 1 dominio (propulsión), no extracción automática masiva de PDFs en V1. Extracción automática (NLP sobre papers) es Phase 9+. |
| 7 | **Alcance físico real del primer PhysicsModel** | La spec pide soportar "las bases necesarias para el dominio seleccionado" sin decir cuál subsistema exacto. | Necesito que confirmes: ¿empezamos con un **thruster eléctrico simple (ej. resistojet o Hall thruster simplificado, 0-D/1-D)** o algo tipo **propulsión química (cohete de gas frío)**? Esto determina el primer `PhysicsModel` concreto de Phase 3/7. Propongo **cold-gas thruster** como primer caso: física simple (conservación de masa/momento, flujo compresible 1-D, ecuación de empuje ideal), bien documentada públicamente, y suficiente para probar todo el pipeline sin ambigüedad. |
| 8 | **Definición de "mejora reproducible" (sección 30)** | No hay umbral estadístico definido. | → Un candidato se considera "mejora" si domina al baseline en Pareto (todas las métricas objetivo iguales o mejores, al menos una estrictamente mejor) **dentro del intervalo de incertidumbre reportado**, no solo en valor puntual. |
| 9 | **Multi-tenancy / multiusuario** | No mencionado. Asumo mono-usuario local para V1. | → Confirmar: sistema mono-usuario, ejecución local, sin auth. Si no, hay que añadir esto a Phase 0. |

Estas 9 decisiones son las que más impactan el resto del documento. Sigo con los defaults propuestos, pero están marcados para tu revisión.

---

## 2. Arquitectura del sistema — vista de capas

```
┌─────────────────────────────────────────────────────────────────┐
│                         DOMAIN PACKS                             │
│   domains/satellite/propulsion/  domains/satellite/thermal/ ...  │
│   (conocimiento, physics models, schemas de requisitos,          │
│    adapters de simulación, métricas — específicos del dominio)   │
└───────────────────────────┬───────────────────────────────────────┘
                             │ implementa interfaces de CORE
┌───────────────────────────▼───────────────────────────────────────┐
│                             CORE                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │ Requirements   │  │ Knowledge      │  │ Design Representation │  │
│  │ Engine         │  │ Engine         │  │                        │  │
│  └───────────────┘  └───────────────┘  └───────────────────────┘  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │ Physics Engine │  │ Numerical      │  │ Simulation Engine      │  │
│  │ (interfaces)   │  │ Engine         │  │                        │  │
│  └───────────────┘  └───────────────┘  └───────────────────────┘  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │ Optimization   │  │ Evaluation     │  │ Verification &          │  │
│  │ Engine         │  │ Engine         │  │ Validation Engine       │  │
│  └───────────────┘  └───────────────┘  └───────────────────────┘  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │ Uncertainty    │  │ Experiment     │  │ Model Registry /        │  │
│  │ Engine         │  │ Memory         │  │ Tool Registry           │  │
│  └───────────────┘  └───────────────┘  └───────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │                       Orchestrator                        │    │
│  └───────────────────────────────────────────────────────────┘    │
└───────────────────────────┬───────────────────────────────────────┘
                             │ usa (via ModelProvider / ToolProvider)
┌───────────────────────────▼───────────────────────────────────────┐
│                        AGENT LAYER                                 │
│  Research Agent · Design Agent · Simulation Agent ·                │
│  Analysis Agent · Critic Agent · Optimization Agent                │
│  (cada uno: LLM + tools autorizadas + estado compartido)           │
└───────────────────────────┬───────────────────────────────────────┘
                             │
┌───────────────────────────▼───────────────────────────────────────┐
│                     INFRASTRUCTURE                                 │
│  Ollama (ModelProvider impl) · SQLite/Postgres · Vector store ·    │
│  Filesystem (docs, artifacts) · Structured logging                 │
└─────────────────────────────────────────────────────────────────────┘
```

**Regla de dependencia:** las flechas de conocimiento van hacia abajo. CORE nunca importa nada de `domains/` ni de `agents/`. Domain Packs implementan interfaces de CORE; nunca al revés. Esto es lo que garantiza que el "mismo núcleo" sirva para estructuras, térmico, semiconductores, etc.

---

## 3. Responsabilidades de módulo (CORE)

| Módulo | Responsabilidad | NO hace |
|---|---|---|
| **Requirements Engine** | Convierte NL → `Requirements` estructurado (Pydantic). Valida dimensionalidad de cada parámetro. | No decide si un requisito es "razonable" físicamente — eso es Critic. |
| **Knowledge Engine** | RAG híbrido: vector search + capa estructurada + provenance. Responde "¿de dónde salió esto?". | No genera hipótesis de diseño. |
| **Design Representation** | Schema universal de `Design` (componentes, geometría, materiales, parámetros). Serializa/clona/versiona. | No sabe simular ni evaluar — es un contenedor de datos. |
| **Physics Engine** | Registro de `PhysicsModel` (interfaz), cada uno con validity_range, unidades, ecuaciones declaradas. | No implementa TODOS los modelos posibles — solo el/los del dominio activo. |
| **Numerical Engine** | Abstracciones sobre NumPy/SciPy: ODE, integración, interpolación, álgebra lineal. | No reimplementa solvers que SciPy ya resuelve bien. |
| **Simulation Engine** | Ejecuta `SimulationSolver`: Design + Model → Results, de forma reproducible e independiente del LLM. | No decide si el resultado es "bueno" — eso es Evaluation. |
| **Optimization Engine** | Search matemática sobre variables libres (Optuna). Single/multi-objective, Pareto. | No usa el LLM para buscar — el LLM solo puede sugerir qué explorar (a través de Design Agent), nunca ejecutar el search. |
| **Evaluation Engine** | Compara BASELINE vs CANDIDATE con métricas, deltas, violaciones. | No afirma "mejora" sin pasar por Uncertainty Engine. |
| **Verification & Validation Engine** | Corre benchmarks contra casos conocidos antes de habilitar Discovery Mode. | No es lo mismo que Critic (V&V valida el *modelo/solver*; Critic ataca el *candidato*). |
| **Critic Engine** | Agente adversarial: busca violaciones, inconsistencias, supuestos rotos. Puede REJECT. | No corrige el diseño — solo lo rechaza o marca con hallazgos. |
| **Uncertainty Engine** | Añade confidence/uncertainty/data_quality a cada resultado. Monte Carlo y sensitivity en fases posteriores. | No "inventa" incertidumbre — si no hay info, marca UNKNOWN. |
| **Experiment Memory** | Persiste el ciclo de vida completo de cada experimento (sección 21) + grafo de experimentos. | No decide qué experimentar — solo registra. |
| **Model Registry** | Mapea roles lógicos (reasoning, coding, embeddings, vision, fast) → modelos concretos vía `ModelProvider`. | No contiene lógica de negocio de ningún agente. |
| **Tool Registry** | Registro explícito y con permisos de qué tools puede invocar cada agente. | No expone acceso irrestricto al OS (sección 24). |
| **Orchestrator** | Máquina de estados que ejecuta el ciclo completo, aplica budgets (sección 35), decide criterios de parada. | No contiene física ni conocimiento de dominio. |

---

## 4. Data Flow (ciclo completo, nivel sistema)

```
User Requirement (NL)
   │
   ▼
Requirements Engine ──► Requirements (Pydantic, validado dimensionalmente)
   │
   ▼
Research Agent ──uses──► Knowledge Engine ──► Extracted Facts + Sources
   │
   ▼
Design Agent ──► Baseline Design (Design Representation)
   │
   ▼
[DISCOVERY MODE]                          [OPTIMIZATION MODE]
Design Agent genera variantes             Optimizer genera variantes
arquitectónicas (LLM-guided)              (búsqueda matemática, Optuna)
   │                                           │
   └───────────────┬───────────────────────────┘
                    ▼
      Dimensional Analysis (gate obligatorio)
                    ▼
      Physics Engine selecciona PhysicsModel aplicable
                    ▼
      Simulation Engine ──► SimulationSolver ──► Results
                    ▼
      Uncertainty Engine ──► Results + confidence/uncertainty
                    ▼
      Evaluation Engine ──► Baseline vs Candidate → metric deltas
                    ▼
      Critic Engine ──► ACCEPT / REJECT + findings
                    ▼
           ACCEPT ──────────────► Optimization Engine (si Optimization Mode)
                    │                       │
                    ▼                       ▼
           Experiment Memory ◄──────────────┘
           (guarda todo: Experiment node + edge desde parent)
                    │
                    ▼
      ¿Budget agotado / convergencia / no-improvement?
           │ no                      │ sí
           ▼                         ▼
      vuelve a generar          Report Generator
      variantes (loop)          (responde las 12 preguntas de sección 43)
```

Cada flecha de este diagrama es un **tool call auditable**, no una llamada de función oculta dentro de un prompt.

---

## 5. Agent Flow

```
                        ┌──────────────────────┐
                        │     Orchestrator      │
                        │  (state machine)       │
                        └──────┬────────────────┘
       state: RESEARCH         │
       ┌────────────────────────┴─────────────────────────┐
       ▼                        ▼                          ▼
 Research Agent           Shared Project State       Tool Registry
 (LLM: reasoning)         (single source of truth,   (permission-scoped
       │                   Pydantic model,             per agent)
       │                   persisted incrementally)
       ▼
 state: DESIGN
 Design Agent (LLM: reasoning/coding) ──► propone Design + variables libres
       ▼
 state: SIMULATE
 Simulation Agent ──► NO razona sobre física; solo invoca
                       run_simulation() con params validados
       ▼
 state: ANALYZE
 Analysis Agent ──► lee Results, arma resumen para Critic/humano
       ▼
 state: CRITIQUE
 Critic Agent ──► ACCEPT/REJECT + findings estructurados
       ▼
 state: OPTIMIZE  (si aplica)
 Optimization Agent ──► sugiere qué variables explorar;
                         Optimization Engine (NO LLM) ejecuta el search
       ▼
 state: DECIDE (Orchestrator) ──► iterar / parar / reportar
```

**Estado compartido:** un único `ProjectState` (Pydantic) versionado, con lock/append-only para evitar memorias aisladas entre agentes (requisito explícito de sección 6). Cada agente lee el estado completo y escribe solo en su sección autorizada (similar a un blackboard pattern).

---

## 6. Model Flow (Ollama / Model Registry)

```
config/models.yaml
─────────────────────
roles:
  reasoning:   { model: "qwen3:32b",        provider: ollama }
  research:    { model: "qwen3:32b",        provider: ollama }
  coding:      { model: "qwen3-coder:30b",  provider: ollama }
  fast:        { model: "qwen3:4b",         provider: ollama }
  embeddings:  { model: "nomic-embed-text", provider: ollama }
  vision:      { model: "qwen2.5-vl",       provider: ollama }   # opcional, si se necesita
```

```
Agent solicita rol lógico (ej. "reasoning")
        │
        ▼
  ModelRegistry.resolve("reasoning")
        │
        ▼
  ModelProvider (interfaz) ──implementado por──► OllamaProvider
        │
        ▼
  OllamaProvider.complete(messages, tools, response_schema)
        │  (usa Ollama /api/chat con format=json_schema cuando
        │   se requiere salida estructurada; usa tools= cuando
        │   el agente necesita invocar Tool Registry)
        ▼
  Respuesta validada contra Pydantic antes de devolverse al agente
```

`ModelProvider` es la única abstracción que agentes/orchestrator conocen. Cambiar de Ollama a otro proveedor (ej. Anthropic API, vLLM) implica escribir una nueva clase que implemente la interfaz — cero cambios en agentes.

---

## 7. Simulation Flow (detalle)

```
Design (validado) + Requirements
        │
        ▼
PhysicsModel.select(design.domain, design.physics_regime)
        │   valida: ¿el design cae dentro de validity_range del modelo?
        │   si no → UNKNOWN / INSUFFICIENT MODEL (no simula "a ciegas")
        ▼
SimulationSolver.build(model, design, numerical_config)
        │
        ▼
SimulationSolver.run() ──► usa Numerical Engine (SciPy) internamente
        │
        ▼
RawResults (arrays, no interpretados)
        │
        ▼
Uncertainty Engine.annotate(RawResults, model.uncertainty_spec)
        │
        ▼
Results (Pydantic: prediction + confidence + uncertainty + model_validity)
```

Todo `SimulationSolver` es determinista dado el mismo input + seed — condición necesaria para reproducibilidad (sección 34).

---

## 8. Experiment Lifecycle

```
1. CREATE   → Experiment(id, parent_id, requirements, design, assumptions,
                          model_ref, solver_config, sources, timestamp,
                          software_version, model_version)  [status=PENDING]
2. RUN      → Simulation Engine ejecuta → status=SIMULATED, results attached
3. EVALUATE → Evaluation Engine compara vs parent/baseline → metrics attached
4. CRITIQUE → Critic Engine → status=ACCEPTED | REJECTED, findings attached
5. STORE    → Experiment Memory persiste el nodo completo (inmutable una
              vez CRITIQUED) + edge en Experiment Graph desde parent
6. QUERY    → Orchestrator consulta el grafo para evitar repetir regiones
              ya exploradas (dedup por hash de parámetros + tolerancia)
```

Un `Experiment` es **inmutable tras su cierre**. Si se quiere "modificarlo", se crea un experimento hijo — esto es lo que permite reconstruir el árbol de decisiones (sección 22) y responder la pregunta 11 de sección 43.

---

## 9. Repository Structure

```
gede/
├── pyproject.toml
├── README.md
├── config/
│   ├── models.yaml              # Model Registry config
│   ├── tools.yaml                # Tool Registry + permisos por agente
│   ├── budgets.yaml               # max_iterations, max_simulations, etc.
│   └── settings.py               # carga config vía Pydantic Settings
│
├── core/
│   ├── requirements/
│   │   ├── schema.py              # Requirements, Parameter, Constraint...
│   │   └── engine.py              # NL → Requirements structuring
│   ├── knowledge/
│   │   ├── schema.py              # Component, Property, Equation, Source...
│   │   ├── vector_store.py        # interfaz VectorStore + impl Chroma
│   │   ├── structured_store.py    # interfaz para hechos/relaciones
│   │   └── engine.py              # RAG orchestration + provenance lookup
│   ├── design/
│   │   ├── schema.py              # Design, Geometry, Material, Interface...
│   │   └── repository.py          # guardar/clonar/versionar/comparar
│   ├── physics/
│   │   ├── interfaces.py          # PhysicsModel (ABC/Protocol)
│   │   └── registry.py            # PhysicsModelRegistry
│   ├── numerical/
│   │   ├── ode.py
│   │   ├── integration.py
│   │   └── interpolation.py
│   ├── simulation/
│   │   ├── interfaces.py          # SimulationSolver (ABC)
│   │   └── engine.py              # Design+Model → Results, reproducible
│   ├── optimization/
│   │   ├── interfaces.py          # Optimizer (ABC)
│   │   └── optuna_backend.py
│   ├── evaluation/
│   │   ├── schema.py              # EvaluationResult
│   │   └── engine.py              # baseline vs candidate
│   ├── validation/
│   │   ├── benchmarks.py          # V&V contra casos conocidos
│   │   └── dimensional_analysis.py
│   ├── critic/
│   │   ├── schema.py              # Finding, Verdict
│   │   └── engine.py
│   ├── uncertainty/
│   │   ├── schema.py              # UncertaintyAnnotation
│   │   └── engine.py              # (V1: básico; Monte Carlo en fase posterior)
│   ├── experiments/
│   │   ├── schema.py              # Experiment, ExperimentGraph
│   │   └── store.py               # ExperimentStore (ABC) + SQLite impl
│   ├── models/
│   │   ├── interfaces.py          # ModelProvider (ABC)
│   │   ├── registry.py            # ModelRegistry
│   │   └── ollama_provider.py     # OllamaProvider(ModelProvider)
│   ├── tools/
│   │   ├── interfaces.py          # ToolProvider, Tool (schema)
│   │   └── registry.py            # ToolRegistry + permisos
│   └── orchestrator/
│       ├── state.py                # ProjectState (shared, Pydantic)
│       ├── state_machine.py        # estados + transiciones
│       └── orchestrator.py         # loop principal, budgets, stopping
│
├── agents/
│   ├── base.py                     # Agent (ABC): usa ModelProvider+Tools
│   ├── research_agent.py
│   ├── design_agent.py
│   ├── simulation_agent.py
│   ├── analysis_agent.py
│   ├── critic_agent.py
│   └── optimization_agent.py
│
├── domains/
│   └── satellite/
│       └── propulsion/
│           ├── knowledge/          # datos curados públicos (fuentes citadas)
│           ├── requirements_schema.py   # extiende Requirements base
│           ├── parameter_schema.py
│           ├── physics_models/
│           │   └── cold_gas_thruster.py  # PhysicsModel concreto (1er caso)
│           ├── simulation_adapters/
│           │   └── cold_gas_solver.py    # SimulationSolver concreto
│           ├── evaluation_metrics.py
│           └── validation_benchmarks.py
│
├── infrastructure/
│   ├── db/
│   │   ├── models.py                # SQLAlchemy/SQLModel tables
│   │   └── migrations/
│   ├── logging/
│   │   └── structured_logger.py
│   └── config_loader.py
│
├── api/                              # (fase posterior) FastAPI opcional
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── benchmarks/                   # V&V tests (sección 31)
│
└── scripts/
    └── run_first_experiment.py       # entrypoint del vertical slice V1
```

**Regla dura de dependencias (enforced con `import-linter` o similar):**
`domains/*` puede importar `core/*`. `core/*` **nunca** importa de `domains/*` ni de `agents/*`. `agents/*` importa de `core/*` pero no al revés.

---

## 10. Interfaces principales (contratos, no implementación)

```python
# core/models/interfaces.py
from abc import ABC, abstractmethod
from pydantic import BaseModel

class ModelProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        *,
        response_schema: type[BaseModel] | None = None,
        tools: list["ToolSpec"] | None = None,
        role: str = "reasoning",
    ) -> "ModelResponse": ...


# core/tools/interfaces.py
class ToolProvider(ABC):
    @abstractmethod
    def get_tools_for_agent(self, agent_name: str) -> list["ToolSpec"]: ...

    @abstractmethod
    async def invoke(self, tool_name: str, args: dict, *, caller: str) -> "ToolResult": ...


# core/physics/interfaces.py
class PhysicsModel(ABC):
    name: str
    validity_range: dict[str, tuple[float, float]]
    required_units: dict[str, str]

    @abstractmethod
    def applies_to(self, design: "Design") -> bool: ...

    @abstractmethod
    def compute(self, inputs: "PhysicsInputs") -> "PhysicsOutputs": ...

    @abstractmethod
    def assumptions(self) -> list[str]: ...


# core/design/schema.py (Design Representation, no interface, es el schema)
class Design(BaseModel):
    id: str
    parent_id: str | None
    domain: str
    components: list["Component"]
    geometry: dict | None
    materials: list["MaterialRef"]
    parameters: dict[str, "Parameter"]
    interfaces: list["ComponentInterface"]
    constraints: list["Constraint"]
    objectives: list["Objective"]
    metadata: dict


# core/simulation/interfaces.py
class SimulationSolver(ABC):
    @abstractmethod
    def declare_inputs(self) -> dict[str, "ParamSpec"]: ...
    @abstractmethod
    def declare_outputs(self) -> dict[str, "ParamSpec"]: ...
    @abstractmethod
    def run(self, design: Design, model: PhysicsModel, *, seed: int | None = None) -> "Results": ...


# core/optimization/interfaces.py
class Optimizer(ABC):
    @abstractmethod
    def suggest(self, search_space: "SearchSpace", history: list["Experiment"]) -> dict: ...
    @abstractmethod
    def is_pareto_optimal(self, candidate: "Results", frontier: list["Results"]) -> bool: ...


# core/evaluation/interfaces.py
class Evaluator(ABC):
    @abstractmethod
    def compare(self, baseline: "Results", candidate: "Results") -> "EvaluationResult": ...


# core/critic/interfaces.py
class Critic(ABC):
    @abstractmethod
    def review(self, design: Design, results: "Results", evaluation: "EvaluationResult") -> "Verdict": ...


# core/experiments/interfaces.py
class ExperimentStore(ABC):
    @abstractmethod
    def save(self, experiment: "Experiment") -> str: ...
    @abstractmethod
    def get(self, experiment_id: str) -> "Experiment": ...
    @abstractmethod
    def get_graph(self, root_id: str) -> "ExperimentGraph": ...
    @abstractmethod
    def find_similar(self, design: Design, tolerance: float) -> list["Experiment"]: ...


# core/knowledge/interfaces.py
class KnowledgeProvider(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list["RetrievedChunk"]: ...
    @abstractmethod
    def get_source(self, claim_id: str) -> "Source": ...
    @abstractmethod
    def extract_facts(self, document_id: str) -> list["ExtractedFact"]: ...


# core/orchestrator/orchestrator.py (contrato, no impl)
class Orchestrator(ABC):
    @abstractmethod
    async def run(self, requirements: "Requirements", *, mode: str, budget: "Budget") -> "Report": ...
```

Todas estas interfaces usan `typing.Protocol` o `ABC` según convenga; lo importante es que **cada Domain Pack implementa `PhysicsModel` y `SimulationSolver` concretos**, y CORE nunca conoce las implementaciones concretas, solo estas interfaces.

---

## 11. Schemas principales (Pydantic — resumen)

```python
class Parameter(BaseModel):
    name: str
    value: float | int | str | None
    unit: str | None
    type: Literal["fixed", "free", "derived", "constrained", "forbidden"]
    range: tuple[float, float] | None
    source: str | None
    uncertainty: float | None
    dependencies: list[str] = []

class Source(BaseModel):
    id: str
    document: str
    page_or_section: str | None
    retrieved_at: datetime
    metadata: dict = {}

class ExtractedFact(BaseModel):
    claim: str
    extracted_value: float | str | None
    unit: str | None
    confidence: float
    source: Source
    date: datetime

class Requirements(BaseModel):
    problem: str
    objectives: list["Objective"]
    constraints: list["Constraint"]
    variables: dict[str, Parameter]
    operating_conditions: dict[str, Parameter]
    validation_requirements: list[str]

class Results(BaseModel):
    experiment_id: str
    predictions: dict[str, float]
    units: dict[str, str]
    confidence: float | Literal["unknown"]
    uncertainty: dict[str, float] | None
    model_validity: Literal["within_range", "extrapolated", "out_of_range"]
    data_quality: Literal["high", "medium", "low", "unknown"]

class EvaluationResult(BaseModel):
    metric_deltas: dict[str, float]
    constraint_violations: list[str]
    improved: bool | Literal["unknown"]
    confidence: float

class Verdict(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]
    findings: list[str]
    dimensional_issues: list[str] = []
    unjustified_conclusions: list[str] = []

class Experiment(BaseModel):
    id: str
    parent_id: str | None
    requirements: Requirements
    design: Design
    assumptions: list[str]
    model_ref: str
    solver_config: dict
    results: Results | None
    metrics: EvaluationResult | None
    verdict: Verdict | None
    sources: list[Source]
    timestamp: datetime
    software_version: str
    model_version: str
    status: Literal["PENDING", "SIMULATED", "EVALUATED", "ACCEPTED", "REJECTED"]

class Budget(BaseModel):
    max_iterations: int
    max_simulations: int
    max_llm_calls: int
    max_runtime_seconds: int
    max_research_calls: int
```

Cada `Parameter` con `unit` obligatorio (o explícitamente `None` para adimensionales) es lo que hace posible el gate de **Dimensional Analysis** antes de cualquier simulación — usando `pint` como librería de unidades, no un validador casero.

---

## 12. Stack tecnológico (V1)

| Categoría | Elección | Motivo |
|---|---|---|
| Lenguaje | Python 3.11+ | Requisito explícito |
| Validación/schemas | Pydantic v2 | Requisito explícito, performance de v2 |
| Numérico | NumPy, SciPy | Requisito explícito |
| Unidades | `pint` | Dimensional Analysis Engine sin reinventar |
| Optimización | Optuna | Requisito explícito, soporta multi-objetivo y Bayesian |
| Vector store | Chroma (embebido) | Cero infraestructura extra para V1 |
| DB relacional | SQLite (vía SQLModel/SQLAlchemy) | Cero setup; migración a Postgres = cambiar URL |
| LLM runtime | Ollama | Requisito explícito |
| Modelos | Qwen3 (reasoning/research), Qwen3-Coder (código), nomic-embed-text (embeddings) | Requisito explícito |
| Tool calling | Ollama structured outputs (`format=json_schema`) + Pydantic validation | Fiabilidad sobre parsing de texto libre |
| Logging estructurado | `structlog` | JSON logs reconstruibles (sección 33) |
| Testing | `pytest` + `hypothesis` (property-based para dimensional analysis) | Cobertura de casos límite físicos |
| Dependency injection | manual, vía constructor injection (sin framework DI) | Simplicidad; el "framework" es solo pasar interfaces por constructor |
| Import boundaries | `import-linter` | Fuerza la regla CORE ↛ domains/agents en CI |

**Dependencias explícitamente NO incluidas en V1:** ningún framework de agentes (LangChain/LangGraph/AutoGen), ningún motor CAD, ningún ML surrogate, sin GPU/CUDA.

---

## 13. Preparación explícita para C++/CUDA

La spec pide que el sistema permita incorporar C++/CUDA después sin rediseño. Esto se logra así:

1. **`SimulationSolver.run()` es la única frontera de rendimiento.** Su firma no depende de NumPy internamente — recibe/devuelve `Results` (Pydantic con arrays serializables). Un solver en C++ se integra como un binding (pybind11) detrás de la misma interfaz `SimulationSolver`, sin tocar Simulation Engine ni ningún agente.
2. **`Numerical Engine` es una fachada**, no lógica dispersa: cuando un método (ej. un solver PDE denso) sea demasiado lento en SciPy, se reemplaza esa función interna por un binding C++, manteniendo la misma firma.
3. **Geometry/Mesh** (`GeometryEngine`, sección 28) se deja como interfaz vacía en V1 — es el candidato más obvio a C++ (mesh generation) cuando exista.
4. **CUDA**: no se prepara nada explícito en V1 más allá de que `PhysicsModel.compute()` recibe/devuelve arrays NumPy — compatibles con CuPy como reemplazo drop-in si algún día se necesita, sin cambiar la interfaz.

No se crean bindings ni stubs de C++ en V1 — solo se garantiza que ningún módulo de más arriba conoce si un solver está en Python o en C++.

---

## 14. Tool System — cómo funciona tool calling

```yaml
# config/tools.yaml
tools:
  search_knowledge:
    handler: core.knowledge.engine:search
    allowed_agents: [research_agent, design_agent, analysis_agent]
  get_source:
    handler: core.knowledge.engine:get_source
    allowed_agents: [research_agent, analysis_agent, critic_agent]
  create_design:
    handler: core.design.repository:create
    allowed_agents: [design_agent]
  modify_design:
    handler: core.design.repository:modify
    allowed_agents: [design_agent, optimization_agent]
  validate_units:
    handler: core.validation.dimensional_analysis:validate
    allowed_agents: [design_agent, simulation_agent]        # obligatorio, no opcional
  run_simulation:
    handler: core.simulation.engine:run
    allowed_agents: [simulation_agent]
  evaluate_design:
    handler: core.evaluation.engine:compare
    allowed_agents: [analysis_agent]
  run_optimizer:
    handler: core.optimization.optuna_backend:suggest
    allowed_agents: [optimization_agent]
  save_experiment:
    handler: core.experiments.store:save
    allowed_agents: [orchestrator]                          # solo el orquestador persiste
```

`ToolRegistry` carga este YAML, valida que cada `allowed_agents` exista, y en runtime `ToolProvider.get_tools_for_agent(agent_name)` filtra qué tools se exponen al `ModelProvider.complete(tools=...)` de cada agente. Un agente **nunca** puede invocar una tool fuera de su lista — se rechaza a nivel de `ToolProvider.invoke()`, no solo por convención de prompt.

---

## 15. Vertical Slice V1 — definición concreta

Este es el "First Experiment" de sección 30, hecho específico:

**Dominio:** `domains/satellite/propulsion/` — **cold-gas thruster** (propulsión de gas frío, 1-D, flujo compresible ideal).

**Baseline:** thruster de gas frío con parámetros públicos típicos (presión de cámara, geometría de tobera, gas propulsor — ej. nitrógeno).

**Flujo ejecutado end-to-end:**
1. `Requirements Engine` estructura: "maximizar empuje específico (Isp) dado un límite de masa de propulsante y presión de cámara máxima".
2. `Research Agent` recupera de knowledge base curada (ecuaciones de flujo compresible, coeficiente de empuje, datos de propulsantes) con provenance.
3. `Design Agent` construye `Design` baseline (geometría de tobera: ángulo, área de garganta, área de salida).
4. `Optimizer` (Optuna) genera variantes del **área de salida de la tobera** (única variable libre en V1, para mantenerlo simple) dentro de rango físico válido.
5. Cada variante pasa por `validate_units` → `PhysicsModel` (ecuaciones de tobera ideal, flujo isentrópico) → `SimulationSolver`.
6. `Evaluation Engine` compara Isp de cada candidato vs baseline.
7. `Critic Agent` revisa: ¿el número de Mach en salida es físicamente razonable? ¿se violó alguna constraint de geometría?
8. `Experiment Memory` guarda cada candidato como nodo hijo del baseline.
9. Al agotar `max_iterations` (budget), se genera el **Report** respondiendo las 12 preguntas de sección 43.

**Por qué este caso y no otro:** física de tobera ideal (flujo compresible 1-D isentrópico) tiene solución analítica cerrada — permite un benchmark de V&V exacto (sección 31) sin ambigüedad, mientras se prueba el pipeline completo.

---

## 16. Tests necesarios (V1)

| Capa | Qué se testea |
|---|---|
| `dimensional_analysis` | Unit tests: detecta unidades incompatibles, conversiones correctas, rechazo de ecuaciones inconsistentes (property-based con `hypothesis` para combinaciones de unidades). |
| `PhysicsModel` (cold gas) | Comparación contra solución analítica conocida (V&V benchmark, sección 31) — tolerancia numérica explícita. |
| `SimulationSolver` | Reproducibilidad: mismo input + seed → mismo output byte-exacto (o dentro de tolerancia de punto flotante). |
| `Design Representation` | Serialización/deserialización round-trip; clonado no comparte referencias mutables. |
| `ExperimentStore` | Guardar → recuperar → grafo reconstruible; inmutabilidad tras cierre. |
| `Evaluator` | Casos donde candidate domina, empata, o es peor que baseline — verificar `improved` correcto. |
| `Critic` | Casos sintéticos con violación de constraint conocida → debe REJECT. |
| `ToolRegistry` | Un agente sin permiso para una tool → `invoke()` lanza excepción, no la ejecuta. |
| `Orchestrator` | Budget agotado → detiene el loop (test explícito anti-infinite-loop, sección 35). |
| Integración end-to-end | El vertical slice completo (sección 15) corre sin error y produce un `Report` válido. |

---

## 17. Riesgos y trade-offs

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Ollama + Qwen3 no soporta tool calling estructurado de forma 100% confiable en todas las versiones. | Agentes podrían generar JSON inválido, rompiendo el pipeline. | Validación Pydantic estricta con reintento acotado (máx N intentos, cuenta contra `max_llm_calls`); si falla, el experimento queda `status=FAILED`, no se inventa un resultado. |
| Orchestrator custom (vs framework) implica más código propio de coordinación. | Más tiempo de desarrollo inicial en Phase 6. | Se acepta como trade-off deliberado a cambio de control total sobre budgets/stopping — requisito explícito de la spec (sección 35). |
| Schema de Knowledge Engine "completo" en V1 (decisión #6) sin población automática. | Riesgo de sobre-diseñar un schema que luego no encaje con extracción real de PDFs. | Se limita a 1 dominio curado manualmente; el schema se revisa en Phase 9 antes de automatizar extracción. |
| SQLite en V1 con `ExperimentGraph` creciendo. | Queries de grafo (parent/child, similar-search) pueden volverse lentas a gran escala. | `find_similar` usa índice sobre hash de parámetros, no full scan; migración a Postgres+recursive CTEs si se necesita antes de multi-dominio. |
| Un solo Physics Model (cold-gas) valida el pipeline pero no valida que la interfaz `PhysicsModel` generalice bien a física más compleja (ej. electromagnetismo). | Podría requerir romper la interfaz al añadir el 2º modelo. | Aceptado: es exactamente el propósito del vertical slice — descubrir esto barato, con 1 dominio, antes de escalar. |

---

## 18. V1 Implementation Plan (fases, con Definition of Done por fase)

| Fase | Entregable | DoD |
|---|---|---|
| **Phase 0 — Architecture** | Este documento + repo scaffold + `pyproject.toml` + CI con `import-linter` y `pytest` | `pytest` corre (vacío) sin error; reglas de import boundary activas |
| **Phase 1 — Core** | Requirements Engine, Design Representation, Experiment Store (SQLite), Model Registry, Tool Registry, Orchestrator básico (sin agentes reales, con stubs) | Se puede crear un `Requirements` → `Design` → `Experiment` vacío y guardarlo/recuperarlo |
| **Phase 2 — Knowledge** | Ingesta de 5-10 documentos curados de propulsión de gas frío, chunking, embeddings, provenance | `search_knowledge()` devuelve chunks con `Source` trazable |
| **Phase 3 — Science** | Dimensional Analysis, `PhysicsModel` interface, `cold_gas_thruster.py`, primer `SimulationSolver`, benchmark V&V vs solución analítica | Benchmark pasa con error < tolerancia definida |
| **Phase 4 — Design** | Parameter spaces, generación/modificación de `Design`, comparación con baseline | Se puede generar una variante y compararla numéricamente con baseline |
| **Phase 5 — Optimization** | Optuna backend, single-objective (Isp), experiment loop con budget | Loop corre N iteraciones, respeta `max_iterations`, se detiene correctamente |
| **Phase 6 — Agents** | Research/Design/Simulation/Analysis/Critic/Optimization Agents reales sobre Ollama | Cada agente usa solo sus tools permitidas; `ProjectState` compartido sin conflictos |
| **Phase 7 — Domain Pack completo** | `domains/satellite/propulsion/` completo con métricas y benchmarks documentados | Vertical slice de sección 15 corre end-to-end |
| **Phase 8 — Discovery Mode** | Modo completo Research→Hypothesis→Design→Simulation→Critic→Optimization→Iteration, Report generator (12 preguntas) | Reporte responde correctamente las 12 preguntas de sección 43 sobre el experimento del vertical slice |
| **Phase 9 — Advanced AI** | (fuera de V1) surrogate models, active learning, extracción automática de conocimiento | No se empieza sin V1 validado |

**V1 = Phases 0–8.** Cada fase, siguiendo la regla de sección 40, se implementa como: explicar → interfaces → schemas → tests → implementar → correr tests → corregir → documentar → siguiente fase. No se pasa a la fase N+1 sin que N deje el sistema ejecutable.

---

## 19. Próximo paso

Con este documento como base, el siguiente paso natural es **Phase 0**: scaffold del repositorio, `pyproject.toml`, configuración de `import-linter`, y estructura vacía de carpetas — sin lógica de negocio todavía, tal como pide la sección 39.

Antes de eso, necesito que confirmes o ajustes las 9 decisiones de la sección 1 (especialmente **#7: cold-gas thruster como primer caso físico**, y **#9: mono-usuario local**), porque cambian directamente el contenido de Phase 3 y Phase 7.
