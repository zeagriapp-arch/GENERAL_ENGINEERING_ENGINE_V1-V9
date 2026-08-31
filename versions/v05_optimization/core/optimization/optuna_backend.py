"""
OptunaOptimizer: implementación concreta de `Optimizer` sobre Optuna.
Soporta single-objective y multi-objective (Pareto front) según cuántos
`Objective` traiga `Requirements` — sin que el caller tenga que saber
cuál es cuál.

Candidatos inválidos (física fuera de rango o constraint duro violado)
se podan explícitamente vía `optuna.TrialPruned()` — nunca se le pasa a
Optuna un valor objetivo inventado para un diseño que no cumple.
"""
from __future__ import annotations

from typing import Optional

import optuna

from core.design.candidate import build_design, check_design_space_constraints, evaluate_requirements
from core.design.design_space import DesignSpace
from core.optimization.interfaces import OptimizationCandidate, OptimizationResult, Optimizer
from core.orchestrator.budget import Budget, BudgetTracker
from core.requirements.schema import Requirements
from core.simulation import engine as simulation_engine

optuna.logging.set_verbosity(optuna.logging.WARNING)


class MissingObjectiveMetricError(ValueError):
    pass


class OptunaOptimizer(Optimizer):
    def __init__(self, sampler: Optional[optuna.samplers.BaseSampler] = None):
        self._sampler_factory = sampler

    def optimize(
        self,
        requirements: Requirements,
        design_space: DesignSpace,
        *,
        budget: Budget,
        seed: Optional[int] = None,
    ) -> OptimizationResult:
        if not requirements.objectives:
            raise MissingObjectiveMetricError("Requirements sin objectives — no hay qué optimizar.")

        directions = ["maximize" if obj.direction == "maximize" else "minimize" for obj in requirements.objectives]
        sampler = self._sampler_factory or optuna.samplers.TPESampler(seed=seed)
        study = optuna.create_study(directions=directions, sampler=sampler)

        tracker = BudgetTracker(budget)
        evaluations: list[OptimizationCandidate] = []

        def objective(trial: optuna.Trial):
            tracker.record_iteration()

            candidate_values = {
                name: trial.suggest_float(name, var.lower_bound, var.upper_bound)
                for name, var in design_space.variables.items()
            }
            design = build_design(requirements, design_space, candidate_values)

            pre_violations = check_design_space_constraints(design_space, candidate_values)
            if pre_violations:
                evaluations.append(
                    OptimizationCandidate(design=design, results=None, passed=False, reasons=pre_violations)
                )
                raise optuna.TrialPruned()

            tracker.record_simulation()
            results = simulation_engine.run(design)
            passed, reasons = evaluate_requirements(requirements, results)

            if not passed:
                evaluations.append(
                    OptimizationCandidate(design=design, results=results, passed=False, reasons=reasons)
                )
                raise optuna.TrialPruned()

            objective_values: dict[str, float] = {}
            for obj in requirements.objectives:
                if obj.metric not in results.predictions:
                    raise MissingObjectiveMetricError(
                        f"Objective '{obj.name}' referencia métrica '{obj.metric}' "
                        f"que no está en los resultados: {list(results.predictions)}"
                    )
                objective_values[obj.name] = results.predictions[obj.metric]

            evaluations.append(
                OptimizationCandidate(
                    design=design, results=results, passed=True, reasons=[], objective_values=objective_values
                )
            )
            return tuple(objective_values[obj.name] for obj in requirements.objectives)

        study.optimize(
            objective,
            n_trials=budget.max_iterations,
            timeout=budget.max_runtime_seconds,
            catch=(),
        )

        best_trials = study.best_trials  # funciona igual para 1 o N objetivos cuando el study se crea con `directions`
        best_designs = [evaluations[t.number] for t in best_trials if t.number < len(evaluations)]

        stopping_reason = "computational_budget_exceeded" if tracker.exceeded() else "search_completed"
        return OptimizationResult(
            best_designs=best_designs,
            all_evaluations=evaluations,
            iterations=tracker.iterations,
            stopping_reason=stopping_reason,
        )
