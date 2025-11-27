from typing import Type, Dict, List
from .base_solver import BaseSolver
from .multi_agent_solver import MultiAgentSolver
from .one_shot_solver import OneShotSolver


class SolverFactory:
    """Factory for creating solver instances by strategy name.

    This factory enables easy switching between different solving strategies
    without changing the calling code. New strategies can be registered
    dynamically.
    """

    _strategies: Dict[str, Type[BaseSolver]] = {
        "multi-agent": MultiAgentSolver,
        "default": MultiAgentSolver,
        "one-shot": OneShotSolver,
        "fast": OneShotSolver,  # Alias for one-shot
    }

    @classmethod
    def create(cls, strategy: str, **kwargs) -> BaseSolver:
        """Create a solver instance.

        Args:
            strategy: Strategy name ("multi-agent", "one-shot", "fast", "default")
            **kwargs: Arguments passed to the solver constructor:
                - workspace_path: Path to workspace directory
                - part: Part number (1 or 2)
                - client: Optional AdventOfCodeClient
                - year: Puzzle year
                - day: Puzzle day
                - progress_callback: Optional progress callback
                - skip_submission: Whether to skip AoC submission
                - correct_answer: Known correct answer for local verification

        Returns:
            Configured solver instance

        Raises:
            ValueError: If strategy name is unknown
        """
        strategy_lower = strategy.lower()
        if strategy_lower not in cls._strategies:
            available = ", ".join(sorted(set(cls._strategies.keys())))
            raise ValueError(f"Unknown strategy '{strategy}'. Available: {available}")

        solver_class = cls._strategies[strategy_lower]
        return solver_class(**kwargs)

    @classmethod
    def register(cls, name: str, solver_class: Type[BaseSolver]) -> None:
        """Register a new solver strategy.

        Allows external code to add new strategies without modifying this file.

        Args:
            name: The strategy name to register
            solver_class: The solver class (must inherit from BaseSolver)
        """
        cls._strategies[name.lower()] = solver_class

    @classmethod
    def available_strategies(cls) -> List[str]:
        """Return list of available strategy names (unique, sorted)."""
        return sorted(set(cls._strategies.keys()))

    @classmethod
    def get_strategy_class(cls, strategy: str) -> Type[BaseSolver]:
        """Get the solver class for a strategy name without instantiating.

        Args:
            strategy: Strategy name

        Returns:
            The solver class

        Raises:
            ValueError: If strategy name is unknown
        """
        strategy_lower = strategy.lower()
        if strategy_lower not in cls._strategies:
            available = ", ".join(sorted(set(cls._strategies.keys())))
            raise ValueError(f"Unknown strategy '{strategy}'. Available: {available}")
        return cls._strategies[strategy_lower]
