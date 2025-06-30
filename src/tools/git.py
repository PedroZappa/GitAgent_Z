import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.tools import tool
from rich.console import Console
from rich.prompt import Confirm

from config.settings import settings
from utils.exceptions import GitCommandError, UnsafeOperationError
from utils.logging import logger
from config.settings import get_git_root

console = Console()

def run_git_command(command: List[str], cwd: Path = None) -> Dict[str, Any]:
    """Execute a git command safely"""
    if not cwd:
        cwd = Path.cwd()
    
    # Validate command is allowed
    if command[0] != "git":
        command = ["git"] + command
    
    git_action = command[1] if len(command) > 1 else ""
    if git_action not in settings.allowed_git_commands:
        raise UnsafeOperationError(f"Git command '{git_action}' not allowed")
    
    try:
        logger.debug(f"Running git command: {' '.join(command)}")
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
            "command": " ".join(command)
        }
    
    except subprocess.TimeoutExpired:
        raise GitCommandError(" ".join(command), -1, "Command timed out")
    except Exception as e:
        raise GitCommandError(" ".join(command), -1, str(e))

@tool
def get_git_status() -> str:
    """Get the current Git repository status"""
    try:
        result = run_git_command(["git", "status", "--porcelain", "-b"])
        if result["success"]:
            if result["stdout"]:
                return f"Git status:\n{result['stdout']}"
            else:
                return "Working directory is clean"
        else:
            return f"Error getting git status: {result['stderr']}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def generate_commit_message() -> str:
    """Generate an AI-powered commit message based on staged changes"""
    try:
        from pathlib import Path
        import os
        
        # Get the git repository root
        git_root = get_git_root()
        if not git_root:
            return "Error: Not in a git repository"
        
        commit_editmsg_path = git_root / ".git" / "COMMIT_EDITMSG"
        
        # Get staged changes (what will be committed)
        result = run_git_command(["git", "diff", "--cached"])
        
        if not result["success"]:
            return f"Error getting staged changes: {result['stderr']}"
        
        if not result["stdout"]:
            return "No staged changes found. Please stage your changes first with 'git add'."
        
        # Get current status for context
        status_result = run_git_command(["git", "status", "--porcelain"])
        
        # Generate commit message using LLM
        from core.llm import OllamaManager
        
        try:
            ollama = OllamaManager()
            
            prompt = f"""
Based on the following git diff of staged changes, generate a concise and informative commit message.

Follow these guidelines:
- Start with a verb in imperative mood (Add, Fix, Update, Remove, etc.)
- Keep the first line under 50 characters
- Be specific about what was changed
- Use conventional commit format if applicable

Staged changes:
{result['stdout']}

Current status:
{status_result.get('stdout', '')}

Generate only the commit message, no quotes or extra text:"""

            generated_message = ollama.llm.invoke(prompt)
            
            # Write to COMMIT_EDITMSG file
            with open(commit_editmsg_path, 'w', encoding='utf-8') as f:
                f.write(generated_message.strip())
            
            return f"Generated commit message and saved to .git/COMMIT_EDITMSG:\n\n{generated_message.strip()}"
            
        except Exception as e:
            return f"Error generating commit message: {str(e)}"
            
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def read_commit_editmsg() -> str:
    """Read the current content of .git/COMMIT_EDITMSG file"""
    try:
        from pathlib import Path
        
        git_root = get_git_root()
        if not git_root:
            return "Error: Not in a git repository"
        
        commit_editmsg_path = git_root / ".git" / "COMMIT_EDITMSG"
        
        if not commit_editmsg_path.exists():
            return "No .git/COMMIT_EDITMSG file found. Start a commit to create one."
        
        with open(commit_editmsg_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if content.strip():
            return f"Current commit message template:\n\n{content}"
        else:
            return "The .git/COMMIT_EDITMSG file is empty."
            
    except Exception as e:
        return f"Error reading COMMIT_EDITMSG: {str(e)}"

@tool
def improve_commit_message() -> str:
    """Read existing COMMIT_EDITMSG and improve it with AI suggestions"""
    try:
        from pathlib import Path
        
        git_root = get_git_root()
        if not git_root:
            return "Error: Not in a git repository"
        
        commit_editmsg_path = git_root / ".git" / "COMMIT_EDITMSG"
        
        # Read existing commit message
        if commit_editmsg_path.exists():
            with open(commit_editmsg_path, 'r', encoding='utf-8') as f:
                existing_message = f.read().strip()
        else:
            existing_message = ""
        
        # Get staged changes for context
        diff_result = run_git_command(["git", "diff", "--cached"])
        
        if not diff_result["success"] or not diff_result["stdout"]:
            return "No staged changes found to analyze."
        
        # Generate improved commit message
        from core.llm import OllamaManager
        
        try:
            ollama = OllamaManager()
            
            prompt = f"""
Improve the following commit message based on the actual staged changes.

Current commit message:
{existing_message or "(empty)"}

Staged changes:
{diff_result['stdout']}

Please provide an improved commit message that:
- Accurately reflects the changes
- Follows conventional commit format
- Is concise but informative
- Uses imperative mood

Generate only the improved commit message:"""

            improved_message = ollama.llm.invoke(prompt)
            
            # Write improved message back to file
            with open(commit_editmsg_path, 'w', encoding='utf-8') as f:
                f.write(improved_message.strip())
            
            return f"Improved commit message:\n\n{improved_message.strip()}\n\nSaved to .git/COMMIT_EDITMSG"
            
        except Exception as e:
            return f"Error improving commit message: {str(e)}"
            
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def get_git_diff(file_path: str = "", generate_commit: bool = False) -> str:
    """Get git diff and optionally generate commit message"""
    try:
        from pathlib import Path
        
        # Determine which diff to show
        if file_path == "--cached" or file_path == "--staged":
            cmd = ["git", "diff", "--cached"]
            diff_type = "staged changes"
        elif file_path:
            cmd = ["git", "diff", file_path]
            diff_type = f"changes in {file_path}"
        else:
            cmd = ["git", "diff"]
            diff_type = "working directory changes"
        
        result = run_git_command(cmd)
        
        if not result["success"]:
            return f"Error getting git diff: {result['stderr']}"
        
        if not result["stdout"]:
            return f"No {diff_type} found"
        
        diff_output = f"Git diff ({diff_type}):\n{result['stdout']}"
        
        # If requested, generate commit message from the diff
        if generate_commit:
            try:
                git_root = get_git_root()
                if git_root:
                    commit_editmsg_path = git_root / ".git" / "COMMIT_EDITMSG"
                    
                    # Generate commit message using the diff
                    from core.llm import OllamaManager
                    ollama = OllamaManager()
                    
                    prompt = f"""
Based on this git diff, generate a concise commit message:

{result['stdout']}

Follow conventional commit guidelines:
- Use imperative mood (Add, Fix, Update, etc.)
- Keep first line under 50 characters
- Be specific and clear

Generate only the commit message:"""

                    commit_message = ollama.llm.invoke(prompt)
                    
                    # Write to COMMIT_EDITMSG
                    with open(commit_editmsg_path, 'w', encoding='utf-8') as f:
                        f.write(commit_message.strip())
                    
                    diff_output += f"\n\n📝 Generated commit message (saved to .git/COMMIT_EDITMSG):\n{commit_message.strip()}"
                    
            except Exception as e:
                diff_output += f"\n\n⚠️ Could not generate commit message: {str(e)}"
        
        return diff_output
        
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def git_add_files(files: str) -> str:
    """Add files to Git staging area. Use '.' for all files"""
    try:
        # Confirm if adding all files
        if files == "." and settings.require_confirmation:
            if not Confirm.ask("Add all files to staging area?"):
                return "Operation cancelled by user"
        
        result = run_git_command(["git", "add", files])
        if result["success"]:
            return f"Successfully added {files} to staging area"
        else:
            return f"Error adding files: {result['stderr']}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def git_commit(message: str) -> str:
    """Commit staged changes with the provided message"""
    try:
        if not message.strip():
            return "Error: Commit message cannot be empty"
        
        result = run_git_command(["git", "commit", "-m", message])
        if result["success"]:
            return f"Successfully committed with message: '{message}'"
        else:
            return f"Error committing: {result['stderr']}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def git_push(remote: str = "origin", branch: str = "") -> str:
    """Push changes to remote repository"""
    try:
        cmd = ["git", "push", remote]
        if branch:
            cmd.append(branch)
        
        if settings.require_confirmation:
            if not Confirm.ask(f"Push to {remote}{f'/{branch}' if branch else ''}?"):
                return "Push cancelled by user"
        
        result = run_git_command(cmd)
        if result["success"]:
            return f"Successfully pushed to {remote}"
        else:
            return f"Error pushing: {result['stderr']}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def git_pull(remote: str = "origin", branch: str = "") -> str:
    """Pull changes from remote repository"""
    try:
               
        cmd = ["git", "pull", remote]
        if branch:
            cmd.append(branch)
        
        result = run_git_command(cmd)
        if result["success"]:
            return f"Successfully pulled from {remote}: {result['stdout']}"
        else:
            return f"Error pulling: {result['stderr']}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def git_log(num_commits: int = 10) -> str:
    """Get git commit history"""
    try:
        result = run_git_command(["git", "log", f"-{num_commits}", "--oneline"])
        if result["success"]:
            if result["stdout"]:
                return f"Recent commits:\n{result['stdout']}"
            else:
                return "No commits found"
        else:
            return f"Error getting git log: {result['stderr']}"
    except Exception as e:
        return f"Error: {str(e)}"

# List of all available tools
GIT_TOOLS = [
    generate_commit_message,  
    read_commit_editmsg,      
    improve_commit_message, 
    get_git_status,
    get_git_diff,
    git_add_files,
    git_commit,
    git_push,
    git_pull,
    git_log,
]


