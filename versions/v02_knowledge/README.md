# v02_knowledge

## Qué contiene

Todo lo de v01_core, más el **Knowledge Engine**:
- Arquitectura híbrida: vector search + capa estructurada + provenance.
- `VectorStore` (coseno sobre SQLite — nota de implementación abajo) + `Embedder` (`HashingEmbedder` offline / `OllamaEmbedder` producción).
- `StructuredKnowledgeStore`: Sources, RawDocuments, Equations, ExtractedFacts.
- 6 fuentes públicas curadas (NASA Glenn Research Center, Wikipedia) sobre ecuaciones de tobera ideal / flujo isentrópico — resumidas en palabras propias, respetando copyright.
- `search_knowledge()`, `get_source()`, `extract_facts()` — provenance completa: toda afirmación se puede rastrear hasta la fuente original.

## Capacidades

Búsqueda semántica sobre conocimiento curado, con trazabilidad completa
("¿de dónde salió este dato?"). Sigue sin PhysicsModel — el
Orchestrator sigue devolviendo `INSUFFICIENT_EVIDENCE`.

## Qué cambió respecto a v01_core

- **Nuevo**: `core/knowledge/` completo, `domains/satellite/propulsion/knowledge/seed_knowledge.py`.
- **Modificado**: `core/models/interfaces.py` y `core/models/ollama_provider.py` ganan el método `embed()`.

## Cómo ejecutarla

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                    # 50 tests
python -m domains.satellite.propulsion.knowledge.seed_knowledge  # sembrar la base
```

## Dependencias

Mismas que v01_core. Sin dependencias nuevas de terceros (no se usa
Chroma real — ver limitación abajo).

## Tests disponibles

50 tests (34 heredados de v01 + 16 nuevos de Knowledge Engine).

## Limitaciones conocidas

- **Vector Store**: la decisión de arquitectura original proponía Chroma
  embebido. Sin acceso de red a modelos de embeddings descargables en el
  entorno de desarrollo, se implementó `SQLiteCosineVectorStore` +
  `HashingEmbedder` (bag-of-words offline, determinista) en su lugar —
  misma interfaz, migrar a Chroma real es una inyección de dependencia,
  no un rediseño.
- Sin extracción automática de conocimiento (NLP sobre PDFs) — la
  curación es manual, deliberadamente (evitar sobre-ingeniería en V1).

## Dependencia de versiones anteriores

Depende de v01_core (mismo código, incluido en esta carpeta). Se
ejecuta de forma independiente.
