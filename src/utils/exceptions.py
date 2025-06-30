"""Custom exceptions for GitAgent_Z"""

class GitAgentException(Exception):
    """Base exception for GitAgent"""
    pass

class OllamaConnectionError(GitAgentException):
    """Raised when cannot connect to Ollama"""
    pass

class GitCommandError(GitAgentException):
    """Raised when Git command fails"""
    def __init__(self, command: str, exit_code: int, stderr: str):
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(f"Git command '{command}' failed with exit code {exit_code}: {stderr}")

class AgentReasoningError(GitAgentException):
    """Raised when agent cannot reason about the task"""
    pass

class UnsafeOperationError(GitAgentException):
    """Raised when attempting unsafe Git operation"""
    pass


