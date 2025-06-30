from rich import print
from rich.panel import Panel
from rich.table import Table
from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Button, Static, Input, 
    RichLog, OptionList, ContentSwitcher, TabPane, TabbedContent
)
from textual.containers import Horizontal, Vertical, Container
from textual.screen import Screen
from textual import on, work

from config.settings import settings
from utils.logging import logger
from utils.exceptions import OllamaConnectionError
from core.llm import OllamaManager, GitPromptManager

class GitAgentApp(App):
    """GitAgent TUI Application"""
    
    CSS_PATH = "styles.tcss"
    
    TITLE = "GitAgent - AI-powered Git Assistant"
    SUB_TITLE = f"Model: {settings.ollama_model}"
    
    def __init__(self):
        super().__init__()
        self.ollama_manager = None
        self.prompt_manager = None
        
        # Predefined prompts from original app
        self.predefined_prompts = {
            "What is my current Git status?": "status",
            "Write a concise standard commit message": "commit",
            "Show me the difference between my working directory and the last commit": "diff",
            "Help me undo my last commit": "undo",
            "I want to push my changes to remote": "push",
            "Help me pull the latest changes from remote": "pull",
            "Explain Git concepts to me": "concepts",
        }

    def compose(self) -> ComposeResult:
        """Create the layout"""
        yield Header()
        
        with Horizontal():
            # Left panel - Menu
            with Vertical(classes="menu-container"):
                yield Static("🚀 Git Operations", classes="menu-title")
                yield OptionList(
                    *self.predefined_prompts.keys(),
                    id="menu"
                )
                yield Button("Custom Prompt", id="custom-btn", variant="primary")
                yield Button("Status Check", id="status-btn", variant="success")
                yield Button("Configuration", id="config-btn", variant="default")
            
            # Right panel - Content
            with Vertical(classes="content-container"):
                yield RichLog(id="output", markup=True)
                yield Input(placeholder="Enter custom prompt...", id="input")
        
        # Status bar
        with Container(classes="status-bar"):
            yield Static("Ready", id="status")
        
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application"""
        self.query_one("#status", Static).update("Initializing GitAgent...")
        
        try:
            self.ollama_manager = OllamaManager()
            self.prompt_manager = GitPromptManager(self.ollama_manager)
            
            # Check health
            is_healthy = await self.ollama_manager.health_check()
            if is_healthy:
                self.query_one("#status", Static).update("✅ Ready - Ollama connected")
                self.log_message("GitAgent initialized successfully!", "success")
            else:
                self.query_one("#status", Static).update("❌ Ollama connection failed")
                self.log_message("Failed to connect to Ollama", "error")
        except OllamaConnectionError as e:
            self.query_one("#status", Static).update(f"❌ Error: {str(e)}")
            self.log_message(f"Failed to connect to Ollama: {e}", "error")
        except Exception as e:
            self.query_one("#status", Static).update(f"❌ Error: {str(e)}")
            self.log_message(f"Initialization error: {e}", "error")

    @on(OptionList.OptionSelected)
    async def handle_menu_selection(self, event: OptionList.OptionSelected) -> None:
        """Handle menu selection"""
        if event.option and event.option.prompt:
            prompt = event.option.prompt
            self.process_request(prompt)

    @on(Button.Pressed, "#custom-btn")
    async def handle_custom_prompt(self) -> None:
        """Focus input for custom prompt"""
        self.query_one("#input", Input).focus()

    @on(Button.Pressed, "#status-btn")
    async def handle_status_check(self) -> None:
        """Show status information"""
        await self.show_status()

    @on(Button.Pressed, "#config-btn")
    async def handle_config_show(self) -> None:
        """Show configuration"""
        await self.show_config()

    @on(Input.Submitted)
    async def handle_input_submitted(self, event: Input.Submitted) -> None:
        """Handle custom prompt submission"""
        if event.value.strip():
            self.process_request(event.value)
            self.query_one("#input", Input).clear()

    @work(thread=True)
    def process_request(self, user_input: str) -> None:
        """Process user request and get AI response"""
        self.call_from_thread(self.log_message, f"**You:** {user_input}", "user")
        self.call_from_thread(lambda: self.query_one("#status", Static).update("🤔 Processing..."))
        
        try:
            if self.prompt_manager:
                response = self.prompt_manager.analyze_git_request(user_input)
                self.call_from_thread(self.log_message, f"**GitAgent:** {response}", "assistant")
            else:
                self.call_from_thread(self.log_message, "GitAgent is not initialized", "error")
        except Exception as e:
            self.call_from_thread(self.log_message, f"❌ Error: {e}", "error")
            logger.error(f"Request processing error: {e}")
        finally:
            self.call_from_thread(lambda: self.query_one("#status", Static).update("✅ Ready"))

    async def show_status(self) -> None:
        """Show system status"""
        status_info = f"""
**GitAgent Status Check**

📁 Config directory: {settings.config_dir}
🤖 Ollama URL: {settings.ollama_base_url}
🧠 Model: {settings.ollama_model}
🌡️ Temperature: {settings.temperature}
🔄 Max Iterations: {settings.max_iterations}
📊 Log Level: {settings.log_level}
        """
        self.log_message(status_info, "info")

    async def show_config(self) -> None:
        """Show configuration details"""
        config_table = Table(title="GitAgent Configuration")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="green")
        
        config_data = {
            "Ollama URL": settings.ollama_base_url,
            "Model": settings.ollama_model,
            "Temperature": str(settings.temperature),
            "Max Iterations": str(settings.max_iterations),
            "Log Level": settings.log_level,
            "Config Dir": str(settings.config_dir),
            "Require Confirmation": str(settings.require_confirmation),
        }
        
        for key, value in config_data.items():
            config_table.add_row(key, value)
        
        self.query_one("#output", RichLog).write(config_table)

    def log_message(self, message: str, msg_type: str = "info") -> None:
        """Log a message to the output"""
        colors = {
            "user": "blue",
            "assistant": "green", 
            "error": "red",
            "success": "green",
            "info": "cyan"
        }
        color = colors.get(msg_type, "white")
        
        panel = Panel(
            message,
            border_style=color,
            title_align="left"
        )
        self.query_one("#output", RichLog).write(panel)

def main():
    """Run the GitAgent TUI"""
    app = GitAgentApp()
    app.run()

def main():
    print(settings)

    return 0


if __name__ == "__main__":
    main()
