from .base_agent import BaseAgent

class TranslationAgent(BaseAgent):

    def __init__(self, workspace_path="./agent_workspace"):
        """Initialize TranslationAgent with workspace path."""
        super().__init__(workspace_path)

    def prompt(self, feedback):
        return """
        You are a translation agent meant to simplify a puzzle.
        This puzzle is written as a whimsical story with many details
        that are irrelevant to the actual task of finding the answer.
        Your goal is to read through the puzzle, think long and hard about it,
        and create a detailed problem report that captures the important information
        from the puzzle. Be sure to include:

        1. What we are trying to solve
        2. What inputs will be given
        3. What the expected output is, including any formatting of output.

        Some context around what we are trying to accomplish may be important to
        keep, so that the agent recieving this report has an idea of why it is
        writing the algorithm at hand.

        The puzzle can be found in puzzle.md
        The input file to the puzzle can be found at input.md
        You should write the problem report you come up with to problem.md
        """