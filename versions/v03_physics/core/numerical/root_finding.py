"""
Numerical Engine — root finding (sección 14).

Fachada delgada sobre SciPy: "no reinventar librerías científicas
existentes sin necesidad". Necesario para resolver relaciones
implícitas como área-Mach en flujo isentrópico (no tiene forma cerrada
para M dado un area ratio).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from scipy.optimize import brentq

from core.numerical.interfaces import ConvergenceStatus, NumericalSolver, NumericalSolverResult


class RootNotBracketedError(ValueError):
    pass


@dataclass
class RootResult:
    root: float
    iterations: int
    converged: bool


def solve_scalar_root(
    func: Callable[[float], float],
    bracket: tuple[float, float],
    *,
    xtol: float = 1e-12,
    maxiter: int = 200,
) -> RootResult:
    """
    Encuentra la raíz de `func` en `bracket` (debe cambiar de signo).
    Envuelve `scipy.optimize.brentq` con manejo de error explícito en
    vez de dejar que una excepción de SciPy se propague sin contexto.
    """
    lo, hi = bracket
    f_lo, f_hi = func(lo), func(hi)
    if f_lo * f_hi > 0:
        raise RootNotBracketedError(
            f"func({lo})={f_lo} y func({hi})={f_hi} tienen el mismo signo — "
            f"no hay garantía de raíz en este bracket."
        )
    root, results = brentq(func, lo, hi, xtol=xtol, maxiter=maxiter, full_output=True)
    return RootResult(root=root, iterations=results.iterations, converged=results.converged)


class RootFindingSolver(NumericalSolver):
    """
    Adapta `solve_scalar_root` a la interfaz común `NumericalSolver`
    (sección 12), para que el `SolverRegistry` pueda encontrarlo junto a
    `ODESolver` bajo el mismo contrato.

    problem_spec esperado: {"func": Callable[[float], float], "bracket": (lo, hi), "xtol": ..., "maxiter": ...}
    """

    solver_id = "scipy-brentq-root"
    name = "SciPy brentq (root finding)"
    problem_types = ["nonlinear", "root"]

    def solve(self, problem_spec: dict) -> NumericalSolverResult:
        try:
            result = solve_scalar_root(
                problem_spec["func"],
                problem_spec["bracket"],
                xtol=problem_spec.get("xtol", 1e-12),
                maxiter=problem_spec.get("maxiter", 200),
            )
        except RootNotBracketedError as exc:
            return NumericalSolverResult(convergence_status=ConvergenceStatus.FAILED, errors=[str(exc)])

        status = ConvergenceStatus.CONVERGED if result.converged else ConvergenceStatus.NOT_CONVERGED
        return NumericalSolverResult(
            values={"root": result.root},
            convergence_status=status,
            iterations=result.iterations,
        )
