"""
SolverRegistry (sección 12): "El Simulation Engine debe poder
seleccionar un solver compatible. No hardcodear la elección del solver
dentro de cada modelo."
"""
from __future__ import annotations

from core.numerical.interfaces import NumericalSolver


class NoSolverAvailableError(LookupError):
    pass


class SolverRegistry:
    def __init__(self):
        self._solvers: dict[str, NumericalSolver] = {}

    def register(self, solver: NumericalSolver) -> None:
        self._solvers[solver.solver_id] = solver

    def get(self, solver_id: str) -> NumericalSolver:
        if solver_id not in self._solvers:
            raise NoSolverAvailableError(f"Solver '{solver_id}' no registrado.")
        return self._solvers[solver_id]

    def find_for_problem_type(self, problem_type: str) -> list[NumericalSolver]:
        return [s for s in self._solvers.values() if problem_type in s.problem_types]
