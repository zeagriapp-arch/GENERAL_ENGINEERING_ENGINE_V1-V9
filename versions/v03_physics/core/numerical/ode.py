"""
Soporte ODE (sección 13) vía SciPy — "no reinventar librerías
científicas existentes sin necesidad".

problem_spec esperado:
    {
        "fun": Callable[[t, y], dy/dt],
        "y0": list[float],
        "t_span": (t0, tf),
        "t_eval": list[float] | None,
        "method": str,           # default "RK45"
        "rtol": float,           # default 1e-8
        "atol": float,           # default 1e-10
        "args": tuple,           # opcional
    }
"""
from __future__ import annotations

import time

import numpy as np
from scipy.integrate import solve_ivp

from core.numerical.interfaces import ConvergenceStatus, NumericalSolver, NumericalSolverResult
from core.numerical.stability import check_array_stability


class ODESolver(NumericalSolver):
    solver_id = "scipy-solve-ivp"
    name = "SciPy solve_ivp (ODE)"
    problem_types = ["ode"]

    def solve(self, problem_spec: dict) -> NumericalSolverResult:
        start = time.monotonic()
        try:
            sol = solve_ivp(
                problem_spec["fun"],
                problem_spec["t_span"],
                problem_spec["y0"],
                method=problem_spec.get("method", "RK45"),
                t_eval=problem_spec.get("t_eval"),
                rtol=problem_spec.get("rtol", 1e-8),
                atol=problem_spec.get("atol", 1e-10),
                args=problem_spec.get("args"),
            )
        except Exception as exc:  # error de configuración/función de usuario, no oculto
            return NumericalSolverResult(
                convergence_status=ConvergenceStatus.FAILED,
                errors=[f"solve_ivp lanzó una excepción: {exc}"],
                runtime_seconds=time.monotonic() - start,
            )

        runtime = time.monotonic() - start
        warnings: list[str] = []

        if not sol.success:
            return NumericalSolverResult(
                values={"t": sol.t.tolist(), "y": sol.y.tolist()},
                convergence_status=ConvergenceStatus.NOT_CONVERGED,
                errors=[sol.message],
                runtime_seconds=runtime,
            )

        stability = check_array_stability(sol.y, name="y")
        if not stability.stable:
            return NumericalSolverResult(
                values={"t": sol.t.tolist(), "y": sol.y.tolist()},
                convergence_status=ConvergenceStatus.DIVERGED,
                errors=stability.notes,
                runtime_seconds=runtime,
            )

        return NumericalSolverResult(
            values={"t": sol.t.tolist(), "y": sol.y.tolist()},
            convergence_status=ConvergenceStatus.CONVERGED,
            iterations=int(sol.nfev),
            warnings=warnings,
            runtime_seconds=runtime,
        )
