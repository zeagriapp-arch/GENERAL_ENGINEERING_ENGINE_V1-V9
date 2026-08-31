"""
Salidas estructuradas de cada agente (sección 38/39: "Toda afirmación
computacional importante debe provenir de resultados verificables" —
por eso NINGÚN schema aquí incluye un veredicto final ni un número de
resultado físico; esos siempre vienen del solver/regla determinista).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ResearchFindings(BaseModel):
    relevant_equations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class DesignProposal(BaseModel):
    values: dict[str, float]
    rationale: str = ""


class AnalysisNarrative(BaseModel):
    narrative: str


class CriticFindings(BaseModel):
    """Solo hallazgos cualitativos adicionales — el veredicto ACCEPT/REJECT nunca sale de aquí."""

    findings: list[str] = Field(default_factory=list)
    risk_level: str = "LOW"  # LOW | MEDIUM | HIGH — informativo, no decisorio


class OptimizationFocus(BaseModel):
    variables_to_explore: list[str] = Field(default_factory=list)
    rationale: str = ""
