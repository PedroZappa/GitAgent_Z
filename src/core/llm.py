from langchain_ollama import OllamaLLM
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
import httpx
import asyncio
from typing import Optional, List
from config.settings import settings
from utils.logging import logger
from utils.exceptions import OllamaConnectionError
from tools.git import GIT_TOOLS

class OllamaManager:
    """Manages Ollama LLM interactions"""
    
    def __init__(self):
        self.llm: Optional[OllamaLLM] = None
        self.agent_executor: Optional[AgentExecutor] = None
        self._initialize_llm()
        self._initialize_agent()
    
    def _initialize_llm(self) -> None:
        """Initialize Ollama LLM connection"""
        try:
            self.llm = OllamaLLM(
                model=settings.ollama_model,
                base_url=settings.ollama_base_url,
                temperature=settings.temperature,
                timeout=settings.ollama_timeout
            )
            logger.info(f"Initialized Ollama with model: {settings.ollama_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama: {e}")
            raise OllamaConnectionError(f"Cannot connect to Ollama: {e}")
    
    def _initialize_agent(self) -> None:
        """Initialize ReAct agent with Git tools"""
        try:
            # Create a more explicit ReAct prompt template
            react_prompt = PromptTemplate.from_template("""
You are a Git expert assistant. Answer questions using the available tools.

Available tools:
{tools}

IMPORTANT FORMATTING RULES:
- Tool names must be EXACT: {tool_names}
- Do NOT add parentheses () to tool names
- Do NOT add quotes around tool names
- Follow the format exactly as shown below

Use this EXACT format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action (as a simple string or JSON)

Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

EXAMPLE:
Question: What is my git status?
Thought: I need to check the current git status
Action: get_git_status
Action Input: 
Observation: Git status: On branch main, nothing to commit, working tree clean
Thought: I now know the final answer
Final Answer: Your git repository is on branch main with a clean working tree.

Begin!

Question: {input}
Thought: {agent_scratchpad}
""")
            
            # Create ReAct agent
            agent = create_react_agent(
                llm=self.llm,
                tools=GIT_TOOLS,
                prompt=react_prompt
            )
            
            # Create agent executor with better error handling
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=GIT_TOOLS,
                max_iterations=settings.max_iterations,
                verbose=True,
                handle_parsing_errors=True,
                early_stopping_method="generate"  # Stop on parsing errors
            )
            
            logger.info("Initialized ReAct agent with Git tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check if Ollama service is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    def process_request(self, user_input: str) -> str:
        """Process user request using the agent"""
        if not self.agent_executor:
            raise OllamaConnectionError("Agent not initialized")
        
        try:
            logger.debug(f"Processing request: {user_input}")
            
            # Check if we're in a git repository for git-related requests
            from config.settings import is_git_repo
            if not is_git_repo():
                git_keywords = ["git", "commit", "push", "pull", "branch", "status", "diff"]
                if any(keyword in user_input.lower() for keyword in git_keywords):
                    return "⚠️  You're not in a Git repository. Please navigate to a Git repository first."
            
            result = self.agent_executor.invoke({"input": user_input})
            return result["output"]
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return f"I encountered an error: {str(e)}. Let me try to help you differently."

class GitPromptManager:
    """Manages Git-specific prompts and responses"""
    
    def __init__(self, ollama_manager: OllamaManager):
        self.ollama = ollama_manager
    
    def analyze_git_request(self, user_request: str, git_status: str = "") -> str:
        """Analyze user's Git request using the agent"""
        return self.ollama.process_request(user_request)

