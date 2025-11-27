from .base_solver import BaseSolver
from src.agents import (
    TranslationAgent, PlanningAgent, CritiqueAgent,
    CodingAgent, TestingAgent, SubmissionAgent
)


class MultiAgentSolver(BaseSolver):
    """Multi-agent solver using the full pipeline.

    This solver uses the complete agent pipeline:
    Translation -> Planning -> Critique -> Revision -> Coding -> Testing -> Submission

    This is the original AdventSolver implementation, providing thorough
    problem analysis and iterative refinement.
    """

    def __init__(self, **kwargs):
        """Initialize MultiAgentSolver with all specialized agents."""
        super().__init__(**kwargs)
        self.translation_agent = TranslationAgent(self.workspace_path, self.part)
        self.planning_agent = PlanningAgent(self.workspace_path, self.part)
        self.critique_agent = CritiqueAgent(self.workspace_path, self.part)
        self.coding_agent = CodingAgent(self.workspace_path, self.part)
        self.testing_agent = TestingAgent(self.workspace_path, self.part)
        self.submission_agent = SubmissionAgent(self.workspace_path, self.part)

    @property
    def strategy_name(self) -> str:
        return "multi-agent"

    def _run_planning_phase(self):
        """Run the planning phase: translation, planning, critique, and plan revision.

        This phase prepares the implementation and test plans before coding begins.
        """
        self._report("translation", "Translating problem description...")
        self.translation_agent.run_agent()

        self._report("planning", "Creating implementation plan...")
        self.planning_agent.run_agent()

        self._report("critique", "Reviewing and critiquing plan...")
        self.critique_agent.run_agent()

        self._report("revision", "Revising plan based on critique...")
        self.planning_agent.run_agent(feedback=True)

    def _run_testing_loop(self):
        """Run the testing/coding feedback loop until tests pass.

        Returns:
            True when tests pass successfully
        """
        test_attempt = 0
        while True:
            test_attempt += 1
            self._report("testing", f"Running tests (attempt {test_attempt})...", attempt=test_attempt)
            results = self.testing_agent.run_agent()
            parsed_result = self.parse_test_result(results)
            if parsed_result:
                return True
            else:
                self._report("coding", f"Adjusting code based on test feedback (attempt {test_attempt})...",
                            attempt=test_attempt)
                self.coding_agent.run_agent(feedback=True)

    def resolve_with_submission_feedback(self):
        """Re-run coding and testing loop with submission feedback.

        Called when a solution passes local tests but fails submission.
        The CodingAgent will read submission_issues.md for guidance.
        """
        self._report("coding", "Adjusting code based on submission feedback...")
        self.coding_agent.run_agent(feedback=True, submission_feedback=True)
        self._run_testing_loop()

    def solve(self) -> bool:
        """Execute the multi-agent solving strategy.

        Pipeline:
        1. Planning phase (translation, planning, critique, revision)
        2. Initial coding
        3. Testing loop (iterate until tests pass)
        4. Submission loop (if client provided)

        Returns:
            True if solution was found and submitted successfully, False otherwise
        """
        # Phase 1: Planning
        self._run_planning_phase()

        # Phase 2: Implementation
        self._report("coding", "Writing initial solution...")
        self.coding_agent.run_agent()

        # Phase 3: Testing loop (runs until tests pass)
        self._run_testing_loop()

        # Phase 4: Submission loop
        return self._run_submission_loop(
            self.submission_agent,
            resolve_callback=self.resolve_with_submission_feedback
        )
