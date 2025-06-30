from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os
from pathlib import Path
import subprocess


def get_git_root():
    """Get the root directory of the current git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def is_git_repo():
    """Check if we're in a git repository."""
    return get_git_root() is not None


def get_config_dir():
    """Get config directory - git root if in repo, otherwise home directory."""
    git_root = get_git_root()
    if git_root:
        return git_root / ".git"
    else:
        return Path.home() / ".git"


class GitAgentSettings(BaseSettings):
    """Configuration settings for GitAgent"""

    # Ollama Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434", description="Ollama server URL"
    )
    ollama_model: str = Field(default="qwen3", description="Ollama model to use")
    ollama_timeout: int = Field(
        default=30, description="Ollama request timeout in seconds"
    )

    # Agent Configuration
    max_iterations: int = Field(default=10, description="Maximum agent iterations")
    temperature: float = Field(default=0.1, description="LLM temperature")

    # Application Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    config_dir: Path = Field(default_factory=get_config_dir)

    # Safety Configuration
    require_confirmation: bool = Field(
        default=True, description="Require confirmation for destructive operations"
    )
    allowed_git_commands: list[str] = Field(
        default_factory=lambda: [
            "status", "add", "commit", "push", "pull", 
            "log", "diff", "stash"

            # "merge", "rebase",
            # "branch", "checkout"
        ]
    )

    # Use model_config instead of Config class for Pydantic v2
    model_config = SettingsConfigDict(
        env_prefix="GITAGENT_",
        env_file=".env",
        case_sensitive=False,
        env_file_encoding="utf-8"
    )

    def model_post_init(self, __context) -> None:
        """Ensure config directory exists - Pydantic v2 method"""
        self.config_dir.mkdir(exist_ok=True, parents=True)


# Global settings instance
settings = GitAgentSettings()

