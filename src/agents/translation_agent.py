from .base_agent import BaseAgent

class TranslationAgent(BaseAgent):

    def __init__(self, workspace_path="./agent_workspace", part=1):
        """Initialize TranslationAgent with workspace path and part number."""
        super().__init__(workspace_path, part)

    def prompt(self, feedback):
        base_prompt = """
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

        if self.part == 2:
            part2_context = """

        IMPORTANT - PART 2 CONTEXT:
        You are solving Part 2 of a multi-part puzzle. Part 2 puzzles are typically
        very brief and assume you have full context from Part 1. To help you:

        - part_1_puzzle.md contains the original full Part 1 puzzle description
        - part_1_problem.md contains the simplified Part 1 problem report
        - part_1_answer.txt contains the answer that was found for Part 1
        - part_1_solution.py contains the code that solved Part 1

        PLEASE READ THESE FILES to understand the full context before creating your
        problem report. Part 2 often builds directly on Part 1's problem, algorithm,
        or answer. Your problem.md should include relevant context from Part 1 so
        that downstream agents understand the complete picture.
        """
            return base_prompt + part2_context

        return base_prompt