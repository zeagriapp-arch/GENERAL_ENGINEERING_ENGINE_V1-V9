"""
Métricas de evaluación específicas del dominio (sección 29). Distinto
del Evaluation Engine genérico de Core: aquí viven comparaciones que
solo tienen sentido para propulsión (ej. eficiencia vs. c* ideal).
"""
from __future__ import annotations

from core.experiments.schema import Results


def isp_efficiency(results: Results, *, theoretical_max_isp: float) -> float | None:
    """
    Qué fracción del Isp teórico máximo (área de salida infinita, misma
    presión/temperatura de cámara) se alcanzó. None si faltan datos —
    nunca se devuelve un número inventado.
    """
    actual = results.predictions.get("specific_impulse")
    if actual is None or theoretical_max_isp <= 0:
        return None
    return actual / theoretical_max_isp


def compare_to_baseline(baseline: Results, candidate: Results) -> dict[str, float]:
    """Deltas porcentuales en las métricas compartidas — determinista, sin LLM."""
    deltas: dict[str, float] = {}
    for key, candidate_value in candidate.predictions.items():
        baseline_value = baseline.predictions.get(key)
        if baseline_value is None or baseline_value == 0:
            continue
        deltas[key] = (candidate_value - baseline_value) / abs(baseline_value)
    return deltas
