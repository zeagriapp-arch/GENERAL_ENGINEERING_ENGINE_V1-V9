"""
Bootstrap de aplicación: el ÚNICO lugar (fuera de tests) que conoce
tanto `core` como `domains` al mismo tiempo. Aquí se registran los
solvers concretos en el Simulation Engine domain-agnóstico — mantiene
la regla core ↛ domains intacta (core/simulation/engine.py nunca
importa `domains`).
"""
from __future__ import annotations

from core.simulation.engine import register_solver
from domains.satellite.propulsion.simulation_adapters.cold_gas_solver import ColdGasNozzleSolver


def bootstrap() -> None:
    register_solver("satellite.propulsion", ColdGasNozzleSolver())
    # Futuros domain packs (structures, thermal, ...) se registran aquí
    # mismo, cada uno con su propio SimulationSolver — sin tocar core/.
