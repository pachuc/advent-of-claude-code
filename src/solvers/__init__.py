"""Solver package for Advent of Code puzzle solving strategies.

This package provides different solving strategies:
- MultiAgentSolver (default): Full pipeline with translation, planning, critique, coding, testing
- OneShotSolver (fast): Direct solving without planning phases

Usage:
    from src.solvers import SolverFactory

    solver = SolverFactory.create("default", workspace_path="./workspace", part=1)
    success = solver.solve()
"""

from .base_solver import BaseSolver
from .multi_agent_solver import MultiAgentSolver
from .one_shot_solver import OneShotSolver
from .solver_factory import SolverFactory

__all__ = [
    "BaseSolver",
    "MultiAgentSolver",
    "OneShotSolver",
    "SolverFactory",
]
