from .base_agent import BaseAgent

class SimpleAgent(BaseAgent):

    def prompt(self, feedback):
        return """
        Analyze what is in this repo and provide a basic description.
        """
