"""Research Agent (sección 7): busca en Knowledge Engine, nunca inventa datos fuera del contexto recuperado."""
from __future__ import annotations

from agents.base import Agent
from agents.schemas import ResearchFindings
from core.requirements.schema import Requirements


class ResearchAgent(Agent):
    name = "research_agent"

    async def research(self, requirements: Requirements, *, top_k: int = 5) -> ResearchFindings:
        tool_result = await self.invoke_tool("search_knowledge", {"query": requirements.problem, "top_k": top_k})
        retrieved = tool_result.value if tool_result.ok else []

        context_lines = []
        for chunk in retrieved or []:
            context_lines.append(f"- [{chunk.source.title}] {chunk.document_title}: {chunk.chunk.text[:300]}")
        context = "\n".join(context_lines) if context_lines else "(sin resultados de knowledge_search)"

        messages = [
            {
                "role": "system",
                "content": (
                    "Eres el Research Agent de un motor de ingeniería. Resume SOLO lo que aparece en el "
                    "contexto recuperado. Nunca inventes ecuaciones, valores o fuentes que no estén en el "
                    "contexto. Si el contexto es insuficiente, dilo explícitamente en open_questions."
                ),
            },
            {"role": "user", "content": f"Problema: {requirements.problem}\n\nContexto recuperado:\n{context}"},
        ]
        return await self.ask(messages, ResearchFindings)
