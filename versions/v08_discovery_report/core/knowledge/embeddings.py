"""
Embedder: abstracción mínima para producir vectores a partir de texto.

Producción: `OllamaEmbedder` (envuelve ModelProvider.embed(), role
'embeddings' del Model Registry — Qwen/nomic-embed-text vía Ollama,
sección 25).

Dev/tests / este sandbox (sin servidor Ollama disponible): `HashingEmbedder`,
100% offline y determinista (hashing trick clásico, sin red ni modelos
descargados). Ambas implementan el mismo protocolo, así que
`KnowledgeEngine` es agnóstico de cuál se use — cambiar de una a otra no
toca ninguna otra parte del sistema.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from core.models.interfaces import ModelProvider


class Embedder(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbedder:
    """Envuelve un ModelProvider real (Phase 6+) para producir embeddings."""

    def __init__(self, provider: ModelProvider, *, role: str = "embeddings"):
        self._provider = provider
        self._role = role

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._provider.embed(texts, role=self._role)


_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


class HashingEmbedder:
    """
    Bag-of-words con hashing trick (sin dependencias externas, sin red).
    NO pretende tener calidad semántica de un embedding neuronal — es un
    sustituto offline suficiente para probar el pipeline de Knowledge
    Engine end-to-end en este entorno. Reemplazar por `OllamaEmbedder` en
    Phase 6 es un cambio de una línea (inyección de dependencia).
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _TOKEN_RE.findall(text.lower())
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]
