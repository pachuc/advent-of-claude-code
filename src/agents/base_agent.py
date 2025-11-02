from abc import ABC, abstractmethod
import subprocess

class ClaudeCodeException(Exception):
    pass

class BaseAgent(ABC):

    def __init__(self, workspace_path="./agent_workspace"):
        """Initialize the agent with a workspace path.

        Args:
            workspace_path: Path to the workspace directory where agents will run
        """
        self.workspace_path = workspace_path

    @abstractmethod
    def prompt(self, feedback):
        pass

    def run_agent(self, feedback=False):
        result = subprocess.run(
            ["claude", "-p", self.prompt(feedback), "--dangerously-skip-permissions"],
            cwd=self.workspace_path,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise Exception(f"Claude Code threw an error: {result.stderr}")
        return result.stdout
        

